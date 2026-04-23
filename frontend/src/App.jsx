import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle2, CircleDashed, ArrowRight, Loader2, Play, Key, Sparkles, Square } from 'lucide-react'

export default function App() {
  const [apiKey, setApiKey] = useState('')
  const [customInstructions, setCustomInstructions] = useState("")
  const [isGeneratingBatch, setIsGeneratingBatch] = useState(false)
  const [batchKeywords, setBatchKeywords] = useState([])
  const [batchError, setBatchError] = useState(null)
  
  const [activeKeyword, setActiveKeyword] = useState(null)
  const [isRunning, setIsRunning] = useState(false)
  const [isBatchRunning, setIsBatchRunning] = useState(false)
  const [state, setState] = useState(null)
  const [currentNode, setCurrentNode] = useState(null)
  const [error, setError] = useState(null)
  const [allFinalArticles, setAllFinalArticles] = useState([])
  
  const stopRequestedRef = useRef(false)

  useEffect(() => {
    const savedKey = localStorage.getItem('gemini_api_key')
    if (savedKey) setApiKey(savedKey)
    const savedInstructions = localStorage.getItem('gemini_custom_instructions')
    if (savedInstructions) setCustomInstructions(savedInstructions)
  }, [])

  const saveApiKey = (val) => {
    setApiKey(val)
    localStorage.setItem('gemini_api_key', val)
  }

  const saveInstructions = (val) => {
    setCustomInstructions(val)
    localStorage.setItem('gemini_custom_instructions', val)
  }

  const generateBatch = async () => {
    if (!apiKey) {
      setBatchError("Please enter your Gemini API Key first.")
      return
    }
    setIsGeneratingBatch(true)
    setBatchError(null)
    try {
      const res = await fetch('http://localhost:8000/api/generate-keywords', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ api_key: apiKey })
      })
      const data = await res.json()
      if (data.error) throw new Error(data.error)
      setBatchKeywords(data.keywords)
    } catch (err) {
      setBatchError(err.message)
    } finally {
      setIsGeneratingBatch(false)
    }
  }
  
  const runWorkflow = async (keywordObj) => {
    if (!apiKey) {
      setError("Please enter your Gemini API Key first.")
      return
    }
    setActiveKeyword(keywordObj.keyword)
    setIsRunning(true)
    setState(null)
    setCurrentNode('scorer')
    setError(null)

    try {
      const response = await fetch('http://localhost:8000/api/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          keyword: keywordObj.keyword, 
          api_key: apiKey,
          custom_instructions: customInstructions
        })
      })

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let done = false

      while (!done) {
        const { value, done: doneReading } = await reader.read()
        done = doneReading
        if (value) {
          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')
          
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const dataStr = line.replace('data: ', '')
              if (dataStr === 'done') {
                setIsRunning(false)
                break
              }
              try {
                const payload = JSON.parse(dataStr)
                setCurrentNode(payload.node)
                setState(payload.state)
              } catch (e) {
                // Ignore parse errors on partial chunks if any
              }
            } else if (line.startsWith('event: error')) {
               // The next line will be data: ...
            }
          }
          
          if (chunk.includes('event: error')) {
             const errorMatch = chunk.match(/data: (.*)/)
             if (errorMatch) {
                setError(errorMatch[1])
                setIsRunning(false)
                break
             }
          }
        }
      }

      // Add to accumulated articles after successful run
      setState((prevState) => {
        if (prevState?.final_articles) {
          setAllFinalArticles(prev => [...prev, ...prevState.final_articles.map(a => ({...a, keyword: keywordObj.keyword}))])
        }
        return prevState
      })

    } catch (err) {
      console.error(err)
      setError(err.message)
      setIsRunning(false)
    }
  }

  const runEntireBatch = async () => {
    setIsBatchRunning(true)
    setAllFinalArticles([])
    stopRequestedRef.current = false
    for (const kw of batchKeywords) {
      if (error) break // stop if fatal error
      if (stopRequestedRef.current) break // stop if user requested
      await runWorkflow(kw)
    }
    setIsBatchRunning(false)
  }
  
  const stopBatch = () => {
    stopRequestedRef.current = true
  }

  const steps = [
    { id: 'scorer', label: 'Keyword Scoring' },
    { id: 'planner', label: 'Content Planning' },
    { id: 'validator', label: 'Outline Validation' },
    { id: 'generator', label: 'RAG Generation' },
    { id: 'reviewer', label: 'Compliance Review' }
  ]

  // Calculate Batch Stats
  const successCount = allFinalArticles.filter(a => a.passed).length;
  const failureCount = allFinalArticles.filter(a => !a.passed).length;
  const failedArticles = allFinalArticles.filter(a => !a.passed);
  
  const categoryStats = {};
  allFinalArticles.forEach(art => {
    const kwObj = batchKeywords.find(k => k.keyword === art.keyword);
    const cat = kwObj ? kwObj.category : "Uncategorized";
    if (!categoryStats[cat]) categoryStats[cat] = { total: 0, success: 0 };
    categoryStats[cat].total++;
    if (art.passed) categoryStats[cat].success++;
  });

  return (
    <div className="max-w-7xl mx-auto p-8 font-sans">
      
      {/* Top Bar Settings */}
      <div className="flex flex-col gap-4 mb-12 glass-panel p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="bg-indigo-600/20 p-2 rounded-lg"><Sparkles className="w-6 h-6 text-indigo-400" /></div>
            <h1 className="text-2xl font-extrabold tracking-tight">
              <span className="gradient-text">ContentForge</span> Pilot
            </h1>
          </div>
          
          <div className="flex items-center gap-4 bg-slate-900/50 p-2 rounded-lg border border-slate-700 w-1/3">
            <Key className="w-5 h-5 text-slate-400 ml-2 shrink-0" />
            <input 
              type="password" 
              value={apiKey}
              onChange={(e) => saveApiKey(e.target.value)}
              placeholder="Enter Gemini API Key..."
              className="bg-transparent border-none text-sm text-slate-200 focus:outline-none w-full placeholder:text-slate-500"
            />
          </div>
        </div>
        
        <div className="border-t border-slate-700 pt-4 mt-2">
          <label className="text-sm font-bold text-indigo-400 mb-2 block uppercase tracking-wider">Additional Batch Instructions (Optional)</label>
          <textarea
            value={customInstructions}
            onChange={(e) => saveInstructions(e.target.value)}
            placeholder="Your core RSOC constraints are hardcoded into the backend. Add any extra context here..."
            className="w-full bg-slate-900/50 border border-slate-700 rounded-lg p-3 text-sm text-slate-200 focus:outline-none focus:border-indigo-500 h-20 resize-none placeholder:text-slate-500"
          />
        </div>
      </div>

      {/* Batch Generator Section */}
      {/* Keyword Generation Section */}
      {!activeKeyword && !isRunning && !state && allFinalArticles.length === 0 && (
        <div className="flex flex-col items-center justify-center py-12">
          <button 
            onClick={generateBatch}
            disabled={isGeneratingBatch}
            className="group relative bg-indigo-600 hover:bg-indigo-500 text-white px-8 py-4 rounded-xl font-bold text-lg transition-all hover:scale-105 shadow-xl shadow-indigo-500/20 flex items-center gap-3 disabled:opacity-50 disabled:hover:scale-100"
          >
            {isGeneratingBatch ? <Loader2 className="animate-spin w-6 h-6" /> : <Sparkles className="w-6 h-6 group-hover:text-indigo-200" />}
            {isGeneratingBatch ? 'Generating Demo Keywords...' : 'Generate Demo Batch (5 Keywords)'}
          </button>
          
          {batchError && <p className="text-red-400 mt-4 text-sm font-medium">{batchError}</p>}
        </div>
      )}

      {batchKeywords.length > 0 && (
            <div className="mt-8">
              <div className="flex justify-between items-center mb-6">
                <h3 className="text-xl font-bold">Generated Keywords ({batchKeywords.length})</h3>
                <div className="flex gap-4">
                  {isBatchRunning && (
                    <button 
                      onClick={stopBatch}
                      className="bg-red-600 hover:bg-red-500 text-white px-6 py-2 rounded-lg font-medium flex items-center gap-2 transition-all shadow-lg shadow-red-500/20"
                    >
                      <Square className="w-4 h-4 fill-current" /> Stop Batch
                    </button>
                  )}
                  <button 
                    onClick={runEntireBatch}
                    disabled={isBatchRunning}
                    className="bg-green-600 hover:bg-green-500 text-white px-6 py-2 rounded-lg font-medium flex items-center gap-2 transition-all disabled:opacity-50"
                  >
                    {isBatchRunning ? <Loader2 className="animate-spin w-4 h-4" /> : <Play className="w-4 h-4" />}
                    {isBatchRunning ? 'Running Batch...' : 'Run Entire Batch Automatically'}
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {batchKeywords.map((kw, i) => (
                  <div key={i} className={`glass-panel p-5 flex flex-col justify-between hover:border-indigo-500/30 transition-colors group ${activeKeyword === kw.keyword ? 'border-indigo-500 shadow-lg shadow-indigo-500/20' : ''}`}>
                    <div>
                      <span className="text-xs font-bold uppercase tracking-wider text-indigo-400 mb-2 block">{kw.category}</span>
                      <h3 className="font-bold text-lg mb-2 text-slate-100">{kw.keyword}</h3>
                      <p className="text-xs text-slate-400 mb-6">{kw.intent} Intent</p>
                    </div>
                    <button 
                      onClick={() => runWorkflow(kw)}
                      disabled={isRunning || isBatchRunning}
                      className="w-full py-2 bg-slate-800 hover:bg-indigo-600 disabled:opacity-50 disabled:hover:bg-slate-800 rounded-lg text-sm font-medium transition-colors flex items-center justify-center gap-2"
                    >
                      {activeKeyword === kw.keyword && (isRunning || isBatchRunning) ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
                      Run Pipeline
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

      {/* Workflow Execution Section */}
      {(activeKeyword || isRunning || state || allFinalArticles.length > 0) && (
        <div>
          <button 
            onClick={() => {
              if (isBatchRunning) return
              setActiveKeyword(null)
              setState(null)
              setCurrentNode(null)
            }}
            disabled={isBatchRunning}
            className="mb-6 text-sm text-indigo-400 hover:text-indigo-300 flex items-center gap-1 disabled:opacity-50"
          >
            ← Back to Keyword Batch
          </button>
          
          {activeKeyword && (
            <div className="mb-8">
              <h2 className="text-2xl font-bold">Processing: <span className="text-indigo-400">{activeKeyword}</span></h2>
              {isBatchRunning && (
                 <p className="text-slate-400 mt-2 flex items-center gap-2"><Loader2 className="w-4 h-4 animate-spin"/> Batch Mode Active - Running autonomously...</p>
              )}
            </div>
          )}

          <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
            {/* Left Col: Workflow Visualizer */}
            <div className="lg:col-span-1 glass-panel p-6 h-fit sticky top-8">
              <h2 className="text-xl font-bold mb-6 flex items-center gap-2">
                Workflow Status
              </h2>
              <div className="space-y-6">
                {steps.map((step, index) => {
                  const isActive = isRunning && currentNode === step.id
                  const isPast = state && Object.keys(state).length > 0 && steps.findIndex(s => s.id === currentNode) > index
                  const isComplete = !isRunning && state?.final_articles?.length > 0

                  return (
                    <div key={step.id} className="relative">
                      {index !== steps.length - 1 && (
                        <div className="absolute left-[11px] top-8 bottom-[-24px] w-[2px] bg-slate-800" />
                      )}
                      <div className={`flex items-center gap-4 ${isActive ? 'opacity-100' : 'opacity-50'}`}>
                        <div className="relative z-10 bg-slate-900 rounded-full">
                          {(isPast || isComplete) ? (
                            <CheckCircle2 className="w-6 h-6 text-green-400" />
                          ) : isActive ? (
                            <Loader2 className="w-6 h-6 text-indigo-400 animate-spin" />
                          ) : (
                            <CircleDashed className="w-6 h-6 text-slate-600" />
                          )}
                        </div>
                        <span className={`font-medium ${isActive ? 'text-indigo-400' : ''}`}>
                          {step.label}
                        </span>
                      </div>
                    </div>
                  )
                })}
              </div>
              
              {state?.status && !error && (
                <div className="mt-8 p-4 bg-slate-900/50 rounded-lg text-sm text-slate-400 font-mono">
                  Status: {state.status}
                </div>
              )}
              
              {error && (
                <div className="mt-8 p-4 bg-red-950/50 border border-red-500/30 rounded-lg text-sm text-red-300 font-mono">
                  <strong>Agent Failure:</strong><br/>
                  {error}
                </div>
              )}
            </div>

            {/* Right Col: Results */}
            <div className="lg:col-span-3 space-y-8">
              <AnimatePresence>
                {state?.score_reasoning && (
                  <motion.div 
                    initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
                    className="glass-panel p-6 border-l-4 border-l-blue-500"
                  >
                    <h3 className="font-bold text-lg mb-2">Keyword Viability: {state.is_viable ? '✅ Approved' : '❌ Rejected'}</h3>
                    <p className="text-slate-300">{state.score_reasoning}</p>
                  </motion.div>
                )}

                {state?.outlines?.length > 0 && (
                  <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="glass-panel p-6">
                    <h3 className="font-bold text-xl mb-4">Generated Plans</h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {state.outlines.map((outline, i) => {
                        const isApproved = state.approved_outlines?.find(o => o.id === outline.id)
                        return (
                          <div key={i} className={`p-4 rounded-xl border ${isApproved ? 'border-green-500/30 bg-green-500/5' : 'border-slate-700 bg-slate-800/50'}`}>
                            <div className="text-xs font-bold uppercase tracking-wider text-indigo-400 mb-2">Variant {outline.id}</div>
                            <div className="font-medium mb-3">{outline.primary_angle}</div>
                            <ul className="space-y-1">
                              {outline.sections.slice(0, 3).map((sec, j) => (
                                <li key={j} className="text-sm text-slate-400 flex items-start gap-2">
                                  <ArrowRight className="w-4 h-4 shrink-0 mt-0.5" />
                                  <span className="truncate">{sec}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )
                      })}
                    </div>
                  </motion.div>
                )}

                {allFinalArticles.length > 0 && (
                  <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6 mt-12 border-t border-slate-700 pt-8">
                    <h3 className="font-bold text-3xl px-2 text-indigo-400 flex items-center gap-3">
                      <Sparkles className="w-8 h-8"/> Batch Execution Dashboard
                    </h3>
                    
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                      <div className="glass-panel p-6 border-l-4 border-l-indigo-500">
                        <div className="text-sm text-slate-400 uppercase tracking-wider font-bold mb-1">Keywords Processed</div>
                        <div className="text-4xl font-extrabold text-white">{batchKeywords.length}</div>
                      </div>
                      <div className="glass-panel p-6 border-l-4 border-l-green-500">
                        <div className="text-sm text-slate-400 uppercase tracking-wider font-bold mb-1">Articles Created</div>
                        <div className="text-4xl font-extrabold text-green-400">{successCount}</div>
                      </div>
                      <div className="glass-panel p-6 border-l-4 border-l-red-500">
                        <div className="text-sm text-slate-400 uppercase tracking-wider font-bold mb-1">Articles Failed</div>
                        <div className="text-4xl font-extrabold text-red-400">{failureCount}</div>
                      </div>
                    </div>

                    <div className="glass-panel p-6 mb-8">
                      <h4 className="text-xl font-bold mb-4 text-white border-b border-slate-700 pb-2">Articles by Category</h4>
                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                        {Object.entries(categoryStats).map(([cat, stats]) => (
                          <div key={cat} className="bg-slate-800/50 p-4 rounded-lg border border-slate-700">
                            <h5 className="font-bold text-indigo-300 uppercase text-xs tracking-wider mb-2">{cat}</h5>
                            <div className="flex justify-between items-center text-sm">
                              <span className="text-slate-300">Generated: {stats.success}</span>
                              <span className="text-slate-500">Total: {stats.total}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {failedArticles.length > 0 && (
                      <div className="glass-panel p-6 border border-red-500/30 bg-red-950/10">
                        <h4 className="text-xl font-bold mb-4 text-red-400 border-b border-red-500/30 pb-2">Failure Report</h4>
                        <div className="space-y-4">
                          {failedArticles.map((art, i) => (
                            <div key={i} className="bg-slate-900/50 p-4 rounded-lg">
                              <div className="flex gap-2 items-center mb-2">
                                <span className="bg-red-500/20 text-red-300 px-2 py-1 rounded text-xs font-bold uppercase tracking-wider">Failed</span>
                                <h5 className="font-bold text-slate-200">{art.title || art.keyword}</h5>
                              </div>
                              <p className="text-sm text-red-300"><strong>Reason:</strong> {art.feedback}</p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        </div>
      )}

    </div>
  )
}

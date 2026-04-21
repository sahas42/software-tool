"use client";

import React, { useState, useRef } from "react";


interface Violation {
  violated_rule: string;
  severity: string;
  code_snippet: string;
  file: string;
  line_range: string;
  explanation: string;
}

interface ComplianceReport {
  is_compliant: boolean;
  summary: string;
  violations: Violation[];
}

export default function Home() {
  const [apiKey, setApiKey] = useState("");
  const [githubUrl, setGithubUrl] = useState("");
  const [rulesFile, setRulesFile] = useState<File | null>(null);
  const [pipelineType, setPipelineType] = useState("advanced");

  // Status mapping
  const [taskId, setTaskId] = useState<string | null>(null);
  const [progress, setProgress] = useState(0);
  const [statusMessage, setStatusMessage] = useState("");
  const [errorObj, setErrorObj] = useState<string | null>(null);
  const [report, setReport] = useState<ComplianceReport | null>(null);

  const wsRef = useRef<WebSocket | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey || !githubUrl || !rulesFile) {
      setErrorObj("Please provide an API Key, GitHub URL, and a set of Rules.");
      return;
    }

    setReport(null);
    setErrorObj(null);
    setProgress(0);
    setStatusMessage("Submitting repository for analysis...");
    setTaskId(null);

    const formData = new FormData();
    formData.append("api_key", apiKey);
    formData.append("codebase_type", "github");
    formData.append("codebase_url", githubUrl);
    formData.append("rules_file", rulesFile);
    formData.append("pipeline_type", pipelineType);
    formData.append("embed_model", "jina");
    formData.append("use_hyde", "true");
    formData.append("extensions", ".py,.js,.ts");

    try {
      const res = await fetch("http://localhost:5001/api/analyze", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        const errorData = await res.json();
        setErrorObj(errorData.error || `Server fault: ${res.status}`);
        setStatusMessage("");
        return;
      }

      const data = await res.json();
      if (!data.task_id) {
        setErrorObj("No task ID returned from backend.");
        setStatusMessage("");
        return;
      }

      setTaskId(data.task_id);
      openWebSocket(data.task_id);

    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Network error. Is the backend running?";
      setErrorObj(msg);
      setStatusMessage("");
    }
  };

  const openWebSocket = (id: string) => {
    const ws = new WebSocket(`ws://localhost:5001/ws/status/${id}`);
    wsRef.current = ws;
    setStatusMessage("Connecting to Celery task queue...");

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      console.log("WebSocket stream:", msg);

      if (msg.progress !== undefined) setProgress(msg.progress);
      if (msg.message && msg.status !== "SUCCESS") setStatusMessage(msg.message);

      if (msg.status === "SUCCESS") {
        setReport(msg.result);
        ws.close();
      } else if (msg.status === "FAILURE") {
        setErrorObj(msg.error || "Celery worker failed.");
        ws.close();
      }
    };

    ws.onerror = () => {
      setErrorObj("WebSocket connection lost. The server may have crashed.");
    };
  };

  return (
    <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6 text-gray-900">
      <main className="w-full max-w-4xl bg-white shadow-xl rounded-2xl overflow-hidden flex flex-col md:flex-row">
        
        {/* Form Column */}
        <div className="w-full md:w-1/2 p-8 border-r border-gray-100 flex flex-col gap-6">
          <div className="space-y-1">
            <h1 className="text-2xl font-bold text-gray-800">Agentic Scanner</h1>
            <p className="text-sm text-gray-500">Run a compliance audit on your codebase.</p>
          </div>

          <form onSubmit={handleSubmit} className="flex flex-col gap-5">
            <div>
              <label className="block text-sm font-medium mb-1">Gemini API Key</label>
              <input 
                type="password"
                className="w-full border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 outline-none"
                placeholder="AIzaSy..."
                value={apiKey}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setApiKey(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">GitHub Repository URL</label>
              <input 
                type="url"
                className="w-full border border-gray-300 rounded-lg p-2.5 focus:ring-2 focus:ring-blue-500 outline-none"
                placeholder="https://github.com/moby/moby"
                value={githubUrl}
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setGithubUrl(e.target.value)}
              />
            </div>

            <div>
              <label className="block text-sm font-medium mb-1">Rules Document (PDF/YAML)</label>
              <input 
                type="file"
                accept=".pdf,.yaml,.yml"
                className="w-full text-sm file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100 border border-gray-300 rounded-lg cursor-pointer p-1"
                onChange={(e: React.ChangeEvent<HTMLInputElement>) => setRulesFile(e.target.files ? e.target.files[0] : null)}
              />
            </div>

            <button 
              type="submit" 
              disabled={!!taskId && !report && !errorObj}
              className="mt-2 bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-semibold py-3 px-4 rounded-lg shadow-md transition-colors"
            >
              Start Analysis Pipeline
            </button>
          </form>

          {errorObj && (
            <div className="p-4 bg-red-50 text-red-700 rounded-lg text-sm font-medium border border-red-200">
              ⚠️ {errorObj}
            </div>
          )}
        </div>

        {/* Results/Loading Column */}
        <div className="w-full md:w-1/2 p-8 bg-gray-50 flex flex-col min-h-[500px]">
          
          {/* Default Start Screen */}
          {!taskId && !report && !errorObj && (
            <div className="flex-1 flex flex-col items-center justify-center text-gray-400 gap-4 text-center">
              <svg className="w-16 h-16 opacity-30" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
              <p>Configure and launch an audit to see your live results and report here.</p>
            </div>
          )}

          {/* WebSocket Live Progress */}
          {taskId && !report && !errorObj && (
            <div className="flex-1 flex flex-col items-center justify-center gap-6">
              <div className="animate-pulse flex items-center justify-center w-16 h-16 bg-blue-100 rounded-full">
                 <div className="w-8 h-8 border-4 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
              </div>
              <div className="w-full max-w-sm space-y-2">
                <div className="flex justify-between text-sm font-medium text-gray-700">
                  <span>{statusMessage || "Processing..."}</span>
                  <span>{progress}%</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2.5 overflow-hidden">
                  <div 
                    className="bg-blue-600 h-2.5 rounded-full transition-all duration-300 ease-out" 
                    style={{ width: `${progress}%` }}
                  ></div>
                </div>
                <p className="text-xs text-gray-400 text-center uppercase tracking-widest mt-4">Task: {taskId.split('-')[0]}</p>
              </div>
            </div>
          )}

          {/* Report Viewer */}
          {report && (
            <div className="flex-1 flex flex-col animate-in fade-in slide-in-from-bottom-4 duration-500">
              <div className={`p-4 rounded-xl border mb-6 ${report.is_compliant ? "bg-green-50 border-green-200" : "bg-red-50 border-red-200"}`}>
                 <h2 className={`text-xl font-bold flex items-center gap-2 ${report.is_compliant ? "text-green-800" : "text-red-800"}`}>
                   {report.is_compliant ? "✅ Fully Compliant" : "❌ Violations Found"}
                 </h2>
                 <p className="text-sm mt-2 opacity-90">{report.summary}</p>
              </div>

              {report.violations && report.violations.length > 0 && (
                <div className="space-y-4 overflow-y-auto max-h-[600px] pr-2 custom-scrollbar">
                  {report.violations.map((v, i: number) => (
                    <div key={i} className="bg-white border hover:border-red-300 border-gray-200 p-4 rounded-xl shadow-sm transition-all text-sm">
                      <div className="flex justify-between items-start mb-3">
                        <span className="font-semibold text-gray-800 break-words flex-1 pr-4">{v.violated_rule}</span>
                        <span className="px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider bg-red-100 text-red-700 flex-shrink-0">
                          {v.severity}
                        </span>
                      </div>
                      <div className="bg-gray-50 border border-gray-100 p-3 rounded-lg font-mono text-xs overflow-x-auto text-gray-600 mb-3 whitespace-pre-wrap">
                        {v.code_snippet}
                      </div>
                      <div>
                        <span className="text-gray-500 text-xs uppercase font-bold tracking-wider">File</span>
                        <p className="text-gray-800 font-medium">{v.file} <span className="text-gray-400 font-normal">lines {v.line_range}</span></p>
                      </div>
                      <div className="mt-2 text-gray-600 leading-relaxed">
                        {v.explanation}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

        </div>
      </main>
    </div>
  );
}

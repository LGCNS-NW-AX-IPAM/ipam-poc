import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Send, User, Bot, Loader2, CheckCircle2, Paperclip, Download } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

function App() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([
    { role: 'assistant', content: '안녕하세요. **IPAM AI Assistant**입니다. 오늘 진행할 IP 회수 작업이 있으신가요?' }
  ]);
  
  const [selectedIps, setSelectedIps] = useState([]);
  const [maxPerTeam, setMaxPerTeam] = useState(4);
  const [excludedFilters, setExcludedFilters] = useState([]);
  const [isConfirmed, setIsConfirmed] = useState(false);
  const [selectedFileName, setSelectedFileName] = useState('');

  const [isLoading, setIsLoading] = useState(false);
  const [expandedExcludedByMsg, setExpandedExcludedByMsg] = useState({});
  const scrollRef = useRef(null);
  const fileInputRef = useRef(null);

  const parseExcludedSection = (content) => {
    const lines = String(content || '').split('\n');
    const headerIdx = lines.findIndex((line) => line.trim() === '제외 목록');
    if (headerIdx < 0) {
      return { hasExcludedSection: false };
    }

    let start = headerIdx + 1;
    while (start < lines.length && !lines[start].trim()) start += 1;
    if (start >= lines.length || !lines[start].trim().startsWith('- ')) {
      return { hasExcludedSection: false };
    }

    let end = start;
    while (end < lines.length) {
      const trimmed = lines[end].trim();
      if (!trimmed) {
        const nextTrimmed = (lines[end + 1] || '').trim();
        if (!nextTrimmed.startsWith('- ')) break;
      } else if (!trimmed.startsWith('- ')) {
        break;
      }
      end += 1;
    }

    const excludedItems = lines.slice(start, end).filter((line) => line.trim().startsWith('- '));
    return {
      hasExcludedSection: true,
      lines,
      listStart: start,
      listEnd: end,
      excludedItems,
    };
  };

  const buildExcludedLimitedMarkdown = (content, isExpanded) => {
    const parsed = parseExcludedSection(content);
    if (!parsed.hasExcludedSection) {
      return {
        markdown: content,
        hasMoreExcluded: false,
        hiddenExcludedCount: 0,
      };
    }

    const limit = 10;
    if (parsed.excludedItems.length <= limit || isExpanded) {
      return {
        markdown: content,
        hasMoreExcluded: parsed.excludedItems.length > limit,
        hiddenExcludedCount: 0,
      };
    }

    const visibleItems = parsed.excludedItems.slice(0, limit);
    const hiddenCount = parsed.excludedItems.length - limit;
    const rebuilt = [
      ...parsed.lines.slice(0, parsed.listStart),
      ...visibleItems,
      `- ...외 ${hiddenCount}건`,
      ...parsed.lines.slice(parsed.listEnd),
    ].join('\n');

    return {
      markdown: rebuilt,
      hasMoreExcluded: true,
      hiddenExcludedCount: hiddenCount,
    };
  };

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const chatHistoryPayload = (msgs) => msgs.map(({ role, content }) => ({ role, content }));

  const downloadReviewExcel = (base64, fileName) => {
    try {
      const bin = atob(base64);
      const arr = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i += 1) arr[i] = bin.charCodeAt(i);
      const blob = new Blob([arr], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = fileName || 'ip_reclaim_candidates_review.xlsx';
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error('다운로드 실패', err);
    }
  };

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = { role: 'user', content: input };
    const updatedMessages = [...messages, userMessage];
    
    setMessages(updatedMessages);
    setInput('');

    setIsLoading(true);

    try {
      const response = await axios.post('http://localhost:8000/api/v1/chat', {
        history: chatHistoryPayload(updatedMessages),
        selected_ips: selectedIps,
        max_per_team: maxPerTeam,
        excluded_filters: excludedFilters,
        is_confirmed: isConfirmed,
      });

      const { content, selected_ips, max_per_team, excluded_filters, is_confirmed } = response.data;

      if (selected_ips) setSelectedIps(selected_ips);
      if (max_per_team) setMaxPerTeam(max_per_team);
      if (excluded_filters !== undefined) setExcludedFilters(excluded_filters);
      if (is_confirmed !== undefined) setIsConfirmed(is_confirmed);

      const assistantMessage = { 
        role: 'assistant', 
        content: content 
      };
      setMessages((prev) => [...prev, assistantMessage]);

    } catch (error) {
      console.error("Error calling /chat API:", error);
      setMessages((prev) => [
        ...prev, 
        { role: 'assistant', content: '죄송합니다. 서버와 통신 중 오류가 발생했습니다. (백엔드 실행 여부를 확인해주세요)' }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const executeCandidateUpload = async () => {
    const file = fileInputRef.current?.files?.[0];
    if (!file || isLoading) return;
    setIsLoading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('history', JSON.stringify(chatHistoryPayload(messages)));
      const response = await axios.post('http://localhost:8000/api/v1/candidate/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });
      const { content, selected_ips, mode, review_excel_base64, batch_id: batchId } = response.data;
      if (selected_ips) setSelectedIps(selected_ips);
      const safeBatch = (batchId || 'review').replace(/[^\w.-]+/g, '_');
      const reviewDl =
        mode === 'extract' && review_excel_base64
          ? { base64: review_excel_base64, fileName: `ip_reclaim_candidates_${safeBatch}.xlsx` }
          : null;
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: content || '업로드 처리가 완료되었습니다.',
          ...(reviewDl ? { reviewExcelDownload: reviewDl } : {}),
        },
      ]);
    } catch (error) {
      console.error('Error calling candidate upload API:', error);
      setMessages((prev) => [...prev, { role: 'assistant', content: '엑셀 업로드 처리 중 오류가 발생했습니다.' }]);
    } finally {
      setIsLoading(false);
      setSelectedFileName('');
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleAttachClick = () => {
    if (!isLoading) fileInputRef.current?.click();
  };

  const handleFileSelected = () => {
    const file = fileInputRef.current?.files?.[0];
    if (!file) return;
    setSelectedFileName(file.name);
    executeCandidateUpload();
  };

  return (
    <div className="flex flex-col h-screen bg-[#343541] text-white font-sans">
      {/* 헤더 */}
      <header className="p-4 border-b border-gray-600 bg-[#202123] flex justify-between items-center shadow-md">
        <div className="flex items-center gap-2">
          <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
          <span className="font-bold text-lg tracking-tight">IPAM AI Agent <span className="text-gray-400 font-normal text-sm">PoC</span></span>
        </div>
        <div className="text-xs text-gray-400 bg-gray-800 px-3 py-1 rounded-full border border-gray-700">
          팀당 제한: {maxPerTeam}개 | 추출됨: {selectedIps.length}건
        </div>
      </header>

      {/* 채팅 메시지 영역 */}
      <main ref={scrollRef} className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6 scroll-smooth">
        {messages.map((msg, index) => (
          <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`flex max-w-[85%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'} items-start gap-3`}>
              <div className={`p-2 rounded-lg shadow-md ${msg.role === 'user' ? 'bg-blue-600' : 'bg-[#10a37f]'}`}>
                {msg.role === 'user' ? <User size={20} /> : <Bot size={20} />}
              </div>
              <div className={`p-4 rounded-2xl shadow-xl leading-relaxed ${
                msg.role === 'user' 
                  ? 'bg-blue-500 text-white rounded-tr-none' 
                  : 'bg-[#444654] text-gray-100 rounded-tl-none border border-gray-600'
              }`}>
                {/* 💡 유저는 일반 텍스트, 어시스턴트는 마크다운 렌더링 */}
                {msg.role === 'user' ? (
                  <p className="whitespace-pre-wrap text-[15px]">{msg.content}</p>
                ) : (
                  <div className="markdown-container text-[15px]">
                    {(() => {
                      const isExpanded = !!expandedExcludedByMsg[index];
                      const {
                        markdown,
                        hasMoreExcluded,
                        hiddenExcludedCount,
                      } = buildExcludedLimitedMarkdown(msg.content, isExpanded);
                      return (
                        <>
                    <ReactMarkdown 
                      remarkPlugins={[remarkGfm]}
                      components={{
                        // 마크다운 요소별 스타일 커스텀
                        table: ({node, ...props}) => (
                          <div className="overflow-x-auto my-3">
                            <table className="border-collapse border border-gray-500 w-full text-sm" {...props} />
                          </div>
                        ),
                        thead: ({node, ...props}) => <thead className="bg-gray-700" {...props} />,
                        th: ({node, ...props}) => <th className="border border-gray-500 px-3 py-2 text-left font-bold" {...props} />,
                        td: ({node, ...props}) => <td className="border border-gray-500 px-3 py-2" {...props} />,
                        ul: ({node, ...props}) => <ul className="list-disc ml-5 my-2 space-y-1" {...props} />,
                        ol: ({node, ...props}) => <ol className="list-decimal ml-5 my-2 space-y-1" {...props} />,
                        li: ({node, ...props}) => <li {...props} />,
                        strong: ({node, ...props}) => <strong className="text-green-400 font-bold" {...props} />,
                        p: ({node, ...props}) => <p className="mb-2 last:mb-0" {...props} />,
                        code: ({node, inline, ...props}) => (
                          <code className={`${inline ? 'bg-gray-800 px-1 rounded' : 'block bg-gray-900 p-2 rounded-md my-2'} font-mono text-sm`} {...props} />
                        )
                      }}
                    >
                      {markdown}
                    </ReactMarkdown>
                          {hasMoreExcluded && (
                            <button
                              type="button"
                              onClick={() =>
                                setExpandedExcludedByMsg((prev) => ({
                                  ...prev,
                                  [index]: !isExpanded,
                                }))
                              }
                              className="mt-2 text-xs text-emerald-300 hover:text-emerald-200 underline underline-offset-2"
                            >
                              {isExpanded ? '제외 목록 접기' : `제외 목록 더보기 (${hiddenExcludedCount}건)`}
                            </button>
                          )}
                        </>
                      );
                    })()}
                  </div>
                )}
                
                {msg.content.includes("확정되었습니다") && (
                  <div className="mt-3 flex items-center gap-2 text-green-400 text-sm font-bold border-t border-gray-600 pt-3">
                    <CheckCircle2 size={16} /> 작업 등록 완료 (NTOSS 연동됨)
                  </div>
                )}
                {msg.role === 'assistant' && msg.reviewExcelDownload && (
                  <div className="mt-3 pt-3 border-t border-gray-600">
                    <button
                      type="button"
                      onClick={() =>
                        downloadReviewExcel(
                          msg.reviewExcelDownload.base64,
                          msg.reviewExcelDownload.fileName
                        )
                      }
                      className="inline-flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-700 hover:bg-emerald-600 text-white text-sm font-medium shadow-md transition-colors"
                    >
                      <Download size={16} />
                      회수 후보 엑셀 다운로드
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start items-center gap-3 animate-pulse">
            <div className="p-2 rounded-lg bg-[#10a37f]">
              <Bot size={20} />
            </div>
            <div className="flex items-center gap-2 text-gray-400">
              <Loader2 className="animate-spin" size={16} />
              <span className="text-sm">에이전트가 데이터 분석 중...</span>
            </div>
          </div>
        )}
      </main>

      {/* 입력 영역 */}
      <footer className="p-6 md:p-10 border-t border-gray-600 bg-[#343541] shadow-2xl">
        <form onSubmit={handleSend} className="max-w-4xl mx-auto relative group">
          <input
            ref={fileInputRef}
            type="file"
            accept=".xlsx,.xlsm,.xltx,.xltm"
            className="hidden"
            onChange={handleFileSelected}
            disabled={isLoading}
          />
          <input
            type="text"
            className="w-full p-4 pl-14 pr-14 rounded-xl bg-[#40414f] border border-gray-600 focus:outline-none focus:border-[#10a37f] focus:ring-1 focus:ring-[#10a37f] text-white placeholder-gray-500 shadow-inner transition-all"
            placeholder="예: 'IP 회수 대상 알려줘', '오늘 IP 회수작업 진행 현황 알려줘'"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
          />
          <button
            type="button"
            onClick={handleAttachClick}
            disabled={isLoading}
            className="absolute left-3 top-1/2 -translate-y-1/2 p-2 rounded-lg text-gray-300 hover:text-white hover:bg-gray-700 disabled:text-gray-500 transition-colors"
            title="엑셀 업로드"
          >
            <Paperclip size={18} />
          </button>
          <button
            type="submit"
            className="absolute right-3 top-1/2 -translate-y-1/2 p-2 rounded-lg text-white bg-[#10a37f] hover:bg-[#1a7f64] disabled:bg-gray-600 disabled:text-gray-400 transition-colors shadow-md"
            disabled={!input.trim() || isLoading}
          >
            <Send size={20} />
          </button>
        </form>
        {selectedFileName && (
          <div className="max-w-4xl mx-auto mt-2 text-xs text-gray-400 truncate">
            첨부됨: {selectedFileName}
          </div>
        )}
        <div className="flex justify-center gap-4 mt-4">
           <p className="text-[11px] text-gray-500 uppercase tracking-widest">
             LG CNS NW AX IPAM PoC Environment
           </p>
        </div>
      </footer>
    </div>
  );
}

export default App;
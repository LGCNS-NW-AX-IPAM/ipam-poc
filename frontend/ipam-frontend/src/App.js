import React, { useState, useRef, useEffect } from 'react';
import axios from 'axios';
import { Send, User, Bot, Loader2 } from 'lucide-react';

function App() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([
    { role: 'assistant', content: '안녕하세요. IPAM 관리 에이전트입니다. 오늘 진행할 IP 회수 작업이 있으신가요?' }
  ]);
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef(null);

  // 새 메시지가 추가될 때마다 하단으로 스크롤
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async (e) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage = { role: 'user', content: input };
    const updatedMessages = [...messages, userMessage];
    
    setMessages(updatedMessages);
    setInput('');
    setIsLoading(true);

    try {
      // 요구사항: /chat API 호출 시 전체 세션 대화 내용을 전송
      const response = await axios.post('http://localhost:8000/api/v1/chat', {
        history: updatedMessages
      });

      const assistantMessage = { 
        role: 'assistant', 
        content: response.data.content 
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error("Error calling /chat API:", error);
      setMessages((prev) => [
        ...prev, 
        { role: 'assistant', content: '죄송합니다. 서버와 통신 중 오류가 발생했습니다.' }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen bg-[#343541] text-white">
      {/* 헤더 */}
      <header className="p-4 border-b border-gray-600 text-center font-bold text-xl">
        IPAM PoC: IP 회수작업
      </header>

      {/* 채팅 메시지 영역 */}
      <main ref={scrollRef} className="flex-1 overflow-y-auto p-4 md:p-8 space-y-6">
        {messages.map((msg, index) => (
          <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`flex max-w-[80%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'} items-start gap-3`}>
              <div className={`p-2 rounded-full ${msg.role === 'user' ? 'bg-blue-600' : 'bg-green-600'}`}>
                {msg.role === 'user' ? <User size={20} /> : <Bot size={20} />}
              </div>
              <div className={`p-4 rounded-2xl ${msg.role === 'user' ? 'bg-blue-500 text-white' : 'bg-gray-700 text-gray-100 shadow-lg'}`}>
                <p className="whitespace-pre-wrap text-sm leading-relaxed">{msg.content}</p>
              </div>
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="flex justify-start items-center gap-3">
            <div className="p-2 rounded-full bg-green-600">
              <Bot size={20} />
            </div>
            <div className="flex items-center gap-2 text-gray-400">
              <Loader2 className="animate-spin" size={16} />
              <span className="text-sm">에이전트가 생각 중...</span>
            </div>
          </div>
        )}
      </main>

      {/* 입력 영역 */}
      <footer className="p-4 md:p-8 border-t border-gray-600 bg-[#343541]">
        <form onSubmit={handleSend} className="max-w-4xl mx-auto relative">
          <input
            type="text"
            className="w-full p-4 pr-12 rounded-xl bg-gray-800 border border-gray-600 focus:outline-none focus:border-blue-500 text-white placeholder-gray-400 shadow-inner"
            placeholder="메시지를 입력하세요 (예: 금일 IP 회수작업 진행 요청)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isLoading}
          />
          <button
            type="submit"
            className="absolute right-3 top-1/2 -translate-y-1/2 p-2 text-blue-400 hover:text-blue-300 disabled:text-gray-600"
            disabled={!input.trim() || isLoading}
          >
            <Send size={24} />
          </button>
        </form>
        <p className="text-center text-[10px] text-gray-500 mt-2">
          IPAM PoC Prototype - Backend Agent Connection Required
        </p>
      </footer>
    </div>
  );
}

export default App;
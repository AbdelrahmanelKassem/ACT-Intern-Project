import { useState } from "react";
import { MessageSquare, X, Send } from "lucide-react";

export default function Chatbot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([{ sender: "bot", text: "Welcome to The Grand Hotel! How can I assist with your stay today?" }]);
  const [input, setInput] = useState("");
  const [sessionId] = useState(() => Math.random().toString(36).substring(7));

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage = { sender: "user", text: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");

    try {
      const response = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, message: input }),
      });
      
      const data = await response.json();
      setMessages((prev) => [...prev, { sender: "bot", text: data.reply }]);
    } catch (error) {
      setMessages((prev) => [...prev, { sender: "bot", text: "Sorry, I'm having trouble connecting to the front desk right now." }]);
    }
  };

  return (
    <div className="fixed bottom-6 left-6 z-50">
      {isOpen ? (
        <div className="w-80 bg-white shadow-2xl rounded-lg overflow-hidden border border-gray-200 flex flex-col h-[400px]">
          <div className="bg-neutral-900 text-white p-4 flex justify-between items-center">
            <h3 className="font-semibold tracking-wide">Concierge</h3>
            <button onClick={() => setIsOpen(false)}><X size={18} /></button>
          </div>
          <div className="flex-1 p-4 overflow-y-auto bg-gray-50 flex flex-col gap-3">
            {messages.map((msg, idx) => (
              <div key={idx} className={`max-w-[80%] p-3 rounded-md text-sm ${msg.sender === "user" ? "bg-neutral-900 text-white self-end" : "bg-white border border-gray-200 text-gray-800 self-start"}`}>
                {msg.text}
              </div>
            ))}
          </div>
          <div className="p-3 bg-white border-t border-gray-200 flex items-center gap-2">
            <input 
              type="text" 
              className="flex-1 p-2 bg-gray-100 rounded text-sm focus:outline-none"
              placeholder="Type your message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            />
            <button onClick={sendMessage} className="p-2 bg-neutral-900 text-white rounded hover:bg-neutral-800"><Send size={16} /></button>
          </div>
        </div>
      ) : (
        <button onClick={() => setIsOpen(true)} className="bg-neutral-900 text-white p-4 rounded-full shadow-lg hover:bg-neutral-800 transition-colors">
          <MessageSquare size={24} />
        </button>
      )}
    </div>
  );
}
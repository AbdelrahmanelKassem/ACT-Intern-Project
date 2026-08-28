import { useState } from "react";
import { MessageSquare, X, Send, Star } from "lucide-react";

export default function Chatbot() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState([{ sender: "bot", text: "Welcome to The Grand Hotel! How can I assist with your stay today?" }]);
  const [input, setInput] = useState("");
  
  // Rating states
  const [isEnded, setIsEnded] = useState(false);
  const [hoveredRating, setHoveredRating] = useState(0);
  const [submitted, setSubmitted] = useState(false);

  // --- CHANGED: Use a dynamically generated UUID for each new session ---
  const [sessionId, setSessionId] = useState(() => crypto.randomUUID());
  
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

  const submitRating = async (rating: number) => {
    try {
      await fetch("http://localhost:8000/rate-session", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId, rating: rating }),
      });
    } catch (error) {
      console.error("Failed to save rating:", error);
    }

    setSubmitted(true);
    
    // Auto-close and reset the chatbot after 2 seconds
    setTimeout(() => {
      setIsOpen(false);
      setTimeout(() => {
        setIsEnded(false);
        setSubmitted(false);
        setMessages([{ sender: "bot", text: "Welcome to The Grand Hotel! How can I assist with your stay today?" }]);
        
        // --- NEW: Generate a fresh session ID for the next user! ---
        setSessionId(crypto.randomUUID());
      }, 500); // Wait for the close animation before resetting
    }, 2000);
  };

  return (
    <div className="fixed bottom-6 left-6 z-50">
      {isOpen ? (
        <div className="w-80 bg-white shadow-2xl rounded-lg overflow-hidden border border-gray-200 flex flex-col h-[400px]">
          {/* Header */}
          <div className="bg-neutral-900 text-white p-4 flex justify-between items-center">
            <h3 className="font-semibold tracking-wide">Concierge</h3>
            <div className="flex items-center gap-4">
              {!isEnded && (
                <button 
                  onClick={() => setIsEnded(true)} 
                  className="text-xs text-gray-300 hover:text-white transition-colors uppercase tracking-wider"
                >
                  End Chat
                </button>
              )}
              <button onClick={() => setIsOpen(false)}><X size={18} /></button>
            </div>
          </div>

          {/* Body */}
          {isEnded ? (
            <div className="flex-1 bg-gray-50 flex flex-col items-center justify-center p-6 text-center">
              {submitted ? (
                <div className="animate-in fade-in duration-500">
                  <h3 className="text-xl font-semibold text-neutral-900 mb-2">Thank You!</h3>
                  <p className="text-sm text-neutral-500">Your feedback helps us maintain our uncompromising standards.</p>
                </div>
              ) : (
                <div className="animate-in fade-in duration-300">
                  <h3 className="text-lg font-semibold text-neutral-900 mb-2">Rate your experience</h3>
                  <p className="text-sm text-neutral-500 mb-6">How did our digital concierge do today?</p>
                  <div className="flex gap-2 justify-center">
                    {[1, 2, 3, 4, 5].map((star) => (
                      <button
                        key={star}
                        onMouseEnter={() => setHoveredRating(star)}
                        onMouseLeave={() => setHoveredRating(0)}
                        onClick={() => submitRating(star)}
                        className="transition-transform hover:scale-110 focus:outline-none"
                      >
                        <Star 
                          size={32} 
                          className={`transition-colors duration-200 ${
                            hoveredRating >= star 
                              ? "fill-yellow-400 text-yellow-400" 
                              : "text-gray-300"
                          }`} 
                        />
                      </button>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : (
            <>
              {/* Chat Messages */}
              <div className="flex-1 p-4 overflow-y-auto bg-gray-50 flex flex-col gap-3">
                {messages.map((msg, idx) => (
                  <div key={idx} className={`max-w-[80%] p-3 rounded-md text-sm ${msg.sender === "user" ? "bg-neutral-900 text-white self-end" : "bg-white border border-gray-200 text-gray-800 self-start"}`}>
                    {msg.text}
                  </div>
                ))}
              </div>
              
              {/* Input Area */}
              <div className="p-3 bg-white border-t border-gray-200 flex items-center gap-2">
                <input 
                  type="text" 
                  className="flex-1 p-2 bg-gray-100 rounded text-sm focus:outline-none"
                  placeholder="Type your message..."
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && sendMessage()}
                />
                <button onClick={sendMessage} className="p-2 bg-neutral-900 text-white rounded hover:bg-neutral-800 transition-colors">
                  <Send size={16} />
                </button>
              </div>
            </>
          )}
        </div>
      ) : (
        <button onClick={() => setIsOpen(true)} className="bg-neutral-900 text-white p-4 rounded-full shadow-lg hover:bg-neutral-800 transition-transform hover:scale-105">
          <MessageSquare size={24} />
        </button>
      )}
    </div>
  );
}
import React, { useState } from "react";
import "./App.css";

function App() {
  const [text, setText] = useState("");
  const [file, setFile] = useState(null);
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  // Handle task extraction
  const handleExtract = async () => {
    if (!text && !file) {
      setMessages((prev) => [
        ...prev,
        { sender: "system", text: "❌ Please provide text or upload a file." },
      ]);
      return;
    }

    setLoading(true);

    const formData = new FormData();
    if (text) formData.append("text", text);
    if (file) formData.append("file", file);

    try {
      const response = await fetch("http://127.0.0.1:8000/extract/", {
        method: "POST",
        body: formData,
      });
      const data = await response.json();
      setMessages((prev) => [
        ...prev,
        { sender: "system", text: data.message || "✅ Meeting notes saved!" },
      ]);
      setText("");
      setFile(null);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { sender: "system", text: "❌ Error extracting tasks. Check backend." },
      ]);
    }

    setLoading(false);
  };

  // Handle question queries
  const handleSend = async () => {
    if (!question.trim()) return;

    const newMsg = { sender: "user", text: question };
    setMessages((prev) => [...prev, newMsg]);
    setQuestion("");
    setLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:8000/chat/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      const data = await response.json();
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: data.answer || "Sorry, I couldn’t find an answer." },
      ]);
    } catch (error) {
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: "⚠️ Failed to reach the backend." },
      ]);
    }

    setLoading(false);
  };

  return (
    <div className="chat-container">
      <h2>Meeting Assistant 💬</h2>

      {/* Text input */}
      <textarea
        rows="5"
        placeholder="Paste your meeting notes here..."
        value={text}
        onChange={(e) => setText(e.target.value)}
      ></textarea>

      {/* File upload */}
      <input
        type="file"
        accept=".docx,.txt,.png,.jpg,.jpeg"
        onChange={(e) => setFile(e.target.files[0])}
      />

      <button onClick={handleExtract} disabled={loading}>
        Extract Tasks
      </button>

      {/* Chatbox */}
      <div className="chatbox">
        {messages.map((msg, index) => (
          <div key={index} className={`msg ${msg.sender}`}>
            {msg.text}
          </div>
        ))}
      </div>

      {/* Question input */}
      <div className="input-row">
        <input
          type="text"
          placeholder="Ask a question..."
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
        />
        <button onClick={handleSend} disabled={loading}>
          Send
        </button>
      </div>
    </div>
  );
}

export default App;

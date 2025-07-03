import React, { useState, useEffect, useRef } from 'react';
import './App.css';

const bgImages = ['bg1.jpg', 'bg2.jpg', 'bg3.jpg'];

function App() {
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([]);
  const [bgIndex, setBgIndex] = useState(0);
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    const interval = setInterval(() => {
      setBgIndex((prev) => (prev + 1) % bgImages.length);
    }, 5000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    if (open && messages.length === 0) {
      setMessages([
        {
          type: 'bot',
          text: `Hi! I’m COSMO, your one stop solution for all things UTD! \n\nHow may I help you today?`
        }
      ]);
    }
  }, [open, messages.length]);

  const sendMessage = async () => {
    if (!question.trim()) return;

    const newMessages = [...messages, { type: 'user', text: question }];
    setMessages(newMessages);
    setQuestion('');
    setIsTyping(true);

    try {
      const res = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      });

      const data = await res.json();
      setMessages((prev) => [...newMessages, { type: 'bot', text: data.response }]);
    } catch (err) {
      setMessages((prev) => [...newMessages, { type: 'bot', text: 'Oops! Something went wrong.' }]);
    } finally {
      setIsTyping(false);
    }
  };

  const decodeHtml = (html) => {
    const txt = document.createElement('textarea');
    txt.innerHTML = html;
    return txt.value;
  };
  
  const formatMessage = (text) => {
    if (!text) return '';
  
    text = decodeHtml(text);
  
    text = text.replace(
      /\[([^\]]+)]\((https?:\/\/[^\s)]+)\)/g,
      '<a href="$2" target="_blank" rel="noopener noreferrer">$1</a>'
    );
  
    text = text.replace(
      /<((https?:\/\/[^\s>]+))>/g,
      '<a href="$1" target="_blank" rel="noopener noreferrer">$1</a>'
    );
  
    return text.replace(/\n/g, '<br/>');
  };
  
  

  return (
    <div
      className="demo-page"
      style={{
        backgroundImage: `url(${process.env.PUBLIC_URL}/${bgImages[bgIndex]})`,
        backgroundSize: 'cover',
        backgroundPosition: 'center',
      }}
    >
      <div className="overlay">
        <div className="landing-wrapper">
          <img
            src={`${process.env.PUBLIC_URL}/cosmo-logo.png`}
            alt="COSMO"
            className="cosmo-logo"
          />
        </div>

        <div className="chat-bubble" onClick={() => setOpen(!open)}>💬</div>

        {open && (
          <div className="chat-window">
            <div className="messages">
              {messages.map((m, i) => (
                <div key={i} className={`message-row ${m.type}`}>
                  {m.type === 'bot' && (
                    <img
                      src={`${process.env.PUBLIC_URL}/temoc.png`}
                      alt="Temoc"
                      className="avatar"
                    />
                  )}
                  <div
                    className={`message ${m.type}`}
                    dangerouslySetInnerHTML={{ __html: formatMessage(m.text) }}
                  ></div>
                </div>
              ))}

              {isTyping && (
                <div className="message-row bot">
                  <img
                    src={`${process.env.PUBLIC_URL}/temoc.png`}
                    alt="Temoc"
                    className="avatar"
                  />
                  <div className="message bot typing-indicator">
                    COSMO is searching the UTD cosmos<span className="dots">...</span>
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            <div className="input">
              <input
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                placeholder="Ask something..."
                onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
              />
              <button onClick={sendMessage}>Send</button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;

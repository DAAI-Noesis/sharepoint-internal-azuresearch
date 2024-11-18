import React, { useState } from 'react';
import userLogo from '../assets/user-logo.png';
import botLogo from '../assets/bot-logo.png';
import './ChatBox.css';

function ChatBox({ onSubmit, messages }) {
    const [userMessage, setUserMessage] = useState("");

    const handleSend = () => {
        if (userMessage) {
            onSubmit(userMessage);
            setUserMessage("");
        }
    };

    const handleKeyPress = (e) => {
        if (e.key === 'Enter') {
            e.preventDefault();  // Prevents Enter key from adding a new line
            handleSend();
        }
    };

    return (
        <div className="chat-box">
            <div className="chat-messages">
                {messages.map((msg, index) => (
                    <div
                        key={index}
                        className={`message ${msg.sender === "user" ? "user-message" : "bot-message"}`}
                    >
                        <img
                            src={msg.sender === "user" ? userLogo : botLogo}
                            alt={`${msg.sender} logo`}
                            className="message-logo"
                        />
                        <div className="message-content">
                            <p>{msg.text}</p>
                            {msg.sender === "bot" && msg.references && msg.references.length > 0 && (
                                <div className="references">
                                    {msg.references.map((ref, refIndex) => (
                                        <button
                                            key={refIndex}
                                            className="reference-button"
                                            onClick={() => window.open(ref.URI, "_blank")}
                                        >
                                            {ref.Name}
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    </div>
                ))}
            </div>
            <div className="chat-input">
                <input
                    type="text"
                    value={userMessage}
                    onChange={(e) => setUserMessage(e.target.value)}
                    onKeyDown={handleKeyPress}  // Handles Enter key
                    placeholder="Type a message..."
                />
                <button onClick={handleSend}>Send</button>
            </div>
        </div>
    );
}

export default ChatBox;

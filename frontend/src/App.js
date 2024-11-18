import React, { useState } from 'react';
import ChatBox from './components/ChatBox';
import FolderList from './components/FolderList';
import axios from 'axios';
import './App.css';

function App() {
    const [messages, setMessages] = useState([
        { text: "Hello! How can I help you today?", sender: "bot" }
    ]);

    const handleFolderSelect = (folder) => {
        // Handle folder selection if needed
    };

    const handleChatSubmit = async (userMessage) => {
        // Add the user message to the chat history
        const updatedMessages = [
            ...messages,
            { text: userMessage, sender: "user" }
        ];
        setMessages(updatedMessages);

        // Prepare chat history for the API call
        const formattedChatHistory = updatedMessages.map((msg) => ({
            role: msg.sender === "user" ? "user" : "assistant",
            content: msg.text
        }));

        try {
            // Make the API call with the user query and formatted chat history
            const response = await axios.post('http://localhost:7071/api/ask/', {
                query: userMessage,
                chat_history: formattedChatHistory
            });

            // Extract response and references from the API response
            const botResponseText = response.data.response;
            const references = response.data.references || [];

            // Add the bot response and references to the chat history
            setMessages((prevMessages) => [
                ...prevMessages,
                { text: botResponseText, sender: "bot", references: references }
            ]);
        } catch (error) {
            console.error("Error fetching bot response:", error);
        }
    };

    return (
        <div className="App">
            <div className="sidebar">
                <FolderList onSelect={handleFolderSelect} />
            </div>
            <div className="chat-container">
                <ChatBox onSubmit={handleChatSubmit} messages={messages} />
            </div>
        </div>
    );
}

export default App;

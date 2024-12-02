import React, { useEffect, useState } from 'react';

function FolderList({ onSelect }) {
    const [folders, setFolders] = useState([]);

    useEffect(() => {
        // Placeholder data for testing
        const mockFolders = [
            { id: "1", name: "Folder A" },
            { id: "2", name: "Folder B" },
            { id: "3", name: "Folder C" },
            { id: "4", name: "Folder D" },
        ];

        // Simulate data fetch delay
        setTimeout(() => {
            setFolders(mockFolders);
        }, 500);  // 500ms delay for testing purposes
    }, []);

    return (
        <div className="folder-list">
            <h2>Folders</h2>
            <div className="folder-buttons">
                {folders.map(folder => (
                    <button
                        key={folder.id}
                        onClick={() => onSelect(folder.name)}
                        className="folder-button"
                    >
                        {folder.name}
                    </button>
                ))}
            </div>
        </div>
    );
}

export default FolderList;

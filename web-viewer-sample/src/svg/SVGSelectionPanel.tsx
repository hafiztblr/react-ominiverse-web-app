import React from 'react';
import '../App.css';

interface SVGSelectionPanelProps {
    onSelect: (entityId: string) => void;
    selectedId: string | null;
}

const SVGSelectionPanel: React.FC<SVGSelectionPanelProps> = ({ onSelect, selectedId }) => {
    return (
        <div className="svg-sidebar">
            <header className="sidebar-header">
                <div className="sidebar-logo">
                    <svg width="30" height="30" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M20 5L35 30H5L20 5Z" fill="#76B900" />
                    </svg>
                    <h2>2D Selection</h2>
                </div>
                <p>Click a component to frame in 3D</p>
            </header>

            <div className="sidebar-svg-container">
                <svg width="100%" height="auto" viewBox="0 0 600 400" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">
                    {/* Background Grid */}
                    <defs>
                        <pattern id="grid-sidebar" width="40" height="40" patternUnits="userSpaceOnUse">
                            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="1" />
                        </pattern>
                        <radialGradient id="sphereGradientSidebar">
                            <stop offset="10%" stopColor="#76B900" />
                            <stop offset="95%" stopColor="#2D4600" />
                        </radialGradient>
                    </defs>
                    <rect width="100%" height="100%" fill="url(#grid-sidebar)" />

                    {/* Interactive Sphere */}
                    <g className={`interactive-group ${selectedId === '438833' ? 'selected' : ''}`} onClick={() => onSelect('438833')} id="438833">
                        <circle cx="150" cy="200" r="40" fill="url(#sphereGradientSidebar)" className="svg-item" />
                        <text x="150" y="260" textAnchor="middle" fill="#aaa" fontSize="12">SPHERE</text>
                    </g>

                    {/* Interactive Cube */}
                    <g className={`interactive-group ${selectedId === '438834' ? 'selected' : ''}`} onClick={() => onSelect('438834')} id="438834">
                        <rect x="270" y="160" width="80" height="80" fill="#444" stroke="#76B900" strokeWidth="2" className="svg-item" />
                        <text x="310" y="260" textAnchor="middle" fill="#aaa" fontSize="12">CUBE</text>
                    </g>

                    {/* Interactive Cone */}
                    <g className={`interactive-group ${selectedId === '438835' ? 'selected' : ''}`} onClick={() => onSelect('438835')} id="438835">
                        <path d="M450 160 L490 240 L410 240 Z" fill="#333" stroke="#aaa" strokeWidth="2" className="svg-item" />
                        <text x="450" y="260" textAnchor="middle" fill="#aaa" fontSize="12">CONE</text>
                    </g>
                </svg>
            </div>
            {/* 
            <div className="sidebar-footer">
                <div className="status-badge-mini">
                    <span className="dot pulse"></span>
                    Direct Memory Link
                </div>
            </div> */}
        </div>
    );
};

export default SVGSelectionPanel;

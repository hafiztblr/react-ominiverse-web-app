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
                    {/* <svg width="30" height="30" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M20 5L35 30H5L20 5Z" fill="#76B900" />
                    </svg> */}
                    <h2>2D Selection</h2>
                </div>
                {/* <p>Click a component to frame in 3D</p> */}
            </header>

            <div className="sidebar-svg-container" style={{ height: 'calc(100% - 100px)', padding: '5px', overflowY: 'auto' }}>
                <svg width="100%" viewBox="0 0 1200 2000" xmlns="http://www.w3.org/2000/svg" preserveAspectRatio="xMidYMid meet">
                    {/* Background Grid */}
                    <defs>
                        <pattern id="grid-sidebar-ultra" width="80" height="80" patternUnits="userSpaceOnUse">
                            <path d="M 80 0 L 0 0 0 80" fill="none" stroke="rgba(255,255,255,0.02)" strokeWidth="1" />
                        </pattern>
                        <linearGradient id="zoneGradientActive" x1="0%" y1="0%" x2="100%" y2="100%">
                            <stop offset="0%" stopColor="rgba(118, 185, 0, 0.4)" />
                            <stop offset="100%" stopColor="rgba(118, 185, 0, 0.1)" />
                        </linearGradient>
                        <pattern id="metal-mesh-ultra" width="15" height="15" patternUnits="userSpaceOnUse">
                            <path d="M 15 0 L 0 15 M 0 0 L 15 15" stroke="rgba(255,255,255,0.05)" strokeWidth="0.5" />
                        </pattern>
                        <pattern id="safety-stripe-ultra" width="30" height="30" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
                            <rect width="15" height="30" fill="rgba(255, 184, 0, 0.05)" />
                        </pattern>
                    </defs>
                    <rect width="100%" height="100%" fill="url(#grid-sidebar-ultra)" />

                    {/* --- LEVEL 1: EXTERIOR --- */}
                    <g className={`interactive-group ${selectedId === 'zone_shell' ? 'selected' : ''}`} onClick={() => onSelect('zone_shell')} id="zone_shell">
                        <rect x="20" y="20" width="1160" height="1960" fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="8" rx="25" className="svg-item" />
                        <text x="600" y="55" textAnchor="middle" fill="#666" fontSize="24" fontWeight="bold">FACTORY EXTERIOR [FRAME ALL]</text>
                    </g>

                    {/* --- LEVEL 2: INFRASTRUCTURE --- */}
                    <g className={`interactive-group ${selectedId === 'zone_lights' ? 'selected' : ''}`} onClick={() => onSelect('zone_lights')} id="zone_lights">
                        <rect x="100" y="100" width="1000" height="100" fill="rgba(255, 255, 0, 0.03)" stroke="#770" rx="50" className="svg-item" />
                        <text x="600" y="160" textAnchor="middle" fill="#AA0" fontSize="26" fontWeight="bold">CEILING LIGHTING SYSTEMS</text>
                    </g>

                    <g className={`interactive-group ${selectedId === 'zone_pipes' ? 'selected' : ''}`} onClick={() => onSelect('zone_pipes')} id="zone_pipes">
                        <path d="M100 250 L1100 250" stroke="#444" strokeWidth="15" strokeLinecap="round" className="svg-item" />
                        <text x="600" y="235" textAnchor="middle" fill="#555" fontSize="18">MAIN PIPING NETWORK</text>
                    </g>

                    <g className={`interactive-group ${selectedId === 'zone_wires' ? 'selected' : ''}`} onClick={() => onSelect('zone_wires')} id="zone_wires">
                        <rect x="100" y="300" width="1000" height="60" fill="rgba(39, 119, 255, 0.1)" stroke="#27F" rx="5" className="svg-item" />
                        <text x="600" y="335" textAnchor="middle" fill="#27F" fontSize="20" fontWeight="bold">ELECTRICAL WIRING & CONDUITS</text>
                    </g>

                    {/* --- LEVEL 3: LOGISTICS & STORAGE --- */}
                    <g className={`interactive-group ${selectedId === 'zone_racks' ? 'selected' : ''}`} onClick={() => onSelect('zone_racks')} id="zone_racks">
                        <rect x="100" y="400" width="1000" height="300" fill="url(#metal-mesh-ultra)" stroke="#555" rx="10" className="svg-item" />
                        <text x="600" y="560" textAnchor="middle" fill="#aaa" fontSize="32" fontWeight="bold">CENTRAL STORAGE & RACKING AREA</text>
                    </g>

                    <g className={`interactive-group ${selectedId === 'zone_hoodrack1' ? 'selected' : ''}`} onClick={() => onSelect('zone_hoodrack1')} id="zone_hoodrack1">
                        <rect x="150" y="420" width="200" height="150" fill="rgba(0,0,0,0.4)" stroke="#aaa" rx="10" className="svg-item" />
                        <text x="250" y="500" textAnchor="middle" fill="#888" fontSize="18">HOOD RACK A</text>
                    </g>

                    <g className={`interactive-group ${selectedId === 'zone_hoodrack2' ? 'selected' : ''}`} onClick={() => onSelect('zone_hoodrack2')} id="zone_hoodrack2">
                        <rect x="400" y="420" width="200" height="150" fill="rgba(0,0,0,0.4)" stroke="#aaa" rx="10" className="svg-item" />
                        <text x="500" y="500" textAnchor="middle" fill="#888" fontSize="18">HOOD RACK B</text>
                    </g>

                    {/* --- LEVEL 4: PRODUCTION CORE --- */}

                    <g className={`interactive-group ${selectedId === 'zone_pedestal' ? 'selected' : ''}`} onClick={() => onSelect('zone_pedestal')} id="zone_pedestal">
                        <circle cx="600" cy="800" r="100" fill="rgba(68, 68, 68, 0.9)" stroke="#76B900" strokeWidth="3" className="svg-item" />
                        <text x="600" y="815" textAnchor="middle" fill="#aaa" fontSize="24" fontWeight="bold">CONTROL PEDESTAL</text>
                    </g>

                    <g className={`interactive-group ${selectedId === 'zone_welding' ? 'selected' : ''}`} onClick={() => onSelect('zone_welding')} id="zone_welding">
                        <rect x="300" y="950" width="600" height="400" fill="url(#zoneGradientActive)" stroke="#76B900" strokeWidth="6" rx="30" className="svg-item" />
                        <circle cx="600" cy="1130" r="100" fill="none" stroke="rgba(118, 185, 0, 0.3)" strokeWidth="3" strokeDasharray="20,10" />
                        <text x="600" y="1150" textAnchor="middle" fill="#76B900" fontSize="42" fontWeight="bold">WELDING ASSEMBLY</text>
                        <text x="600" y="1190" textAnchor="middle" fill="#555" fontSize="20">PRIMARY PRODUCTION AUTOMATION</text>
                    </g>

                    {/* --- LEVEL 5: STATIONS & TRANSFERS --- */}

                    <g className={`interactive-group ${selectedId === 'zone_robots' ? 'selected' : ''}`} onClick={() => onSelect('zone_robots')} id="zone_robots">
                        <rect x="100" y="1400" width="300" height="350" fill="rgba(68, 68, 68, 0.4)" stroke="#76B900" rx="20" className="svg-item" />
                        <text x="250" y="1600" textAnchor="middle" fill="#76B900" fontSize="28" fontWeight="bold">ROBOT ARMS</text>
                    </g>

                    <g className={`interactive-group ${selectedId === 'zone_car_lift' ? 'selected' : ''}`} onClick={() => onSelect('zone_car_lift')} id="zone_car_lift">
                        <rect x="800" y="1400" width="300" height="350" fill="rgba(118, 185, 0, 0.05)" stroke="#76B900" rx="20" className="svg-item" />
                        <path d="M850 1575 L1050 1575" stroke="#444" strokeWidth="20" />
                        <text x="950" y="1625" textAnchor="middle" fill="#76B900" fontSize="28" fontWeight="bold">CAR LIFT</text>
                    </g>

                    <g className={`interactive-group ${selectedId === 'zone_hanger' ? 'selected' : ''}`} onClick={() => onSelect('zone_hanger')} id="zone_hanger">
                        <rect x="450" y="1400" width="300" height="350" fill="rgba(255,255,255,0.02)" stroke="#aaa" rx="20" className="svg-item" />
                        <text x="600" y="1600" textAnchor="middle" fill="#888" fontSize="28" fontWeight="bold">MAINTENANCE HANGER</text>
                    </g>

                    {/* --- LEVEL 6: SAFETY & FLOOR --- */}

                    <g className={`interactive-group ${selectedId === 'zone_fencing' ? 'selected' : ''}`} onClick={() => onSelect('zone_fencing')} id="zone_fencing">
                        <rect x="60" y="700" width="200" height="650" fill="url(#safety-stripe-ultra)" stroke="#FFB800" rx="10" className="svg-item" />
                        <text x="160" y="1050" textAnchor="middle" fill="#FFB800" fontSize="22" fontWeight="bold" transform="rotate(-90, 160, 1050)">SAFETY PERIMETER</text>
                    </g>

                    <g className={`interactive-group ${selectedId === 'zone_paintlines' ? 'selected' : ''}`} onClick={() => onSelect('zone_paintlines')} id="zone_paintlines">
                        <path d="M950 700 L950 1350" stroke="#FFD700" strokeWidth="15" strokeDasharray="30,15" className="svg-item" />
                        <text x="1000" y="1025" textAnchor="middle" fill="#FFD700" fontSize="22" transform="rotate(90, 1000, 1025)">LOGISTICS TRAFFIC LINES</text>
                    </g>

                    <g className={`interactive-group ${selectedId === 'zone_catwalk' ? 'selected' : ''}`} onClick={() => onSelect('zone_catwalk')} id="zone_catwalk">
                        <path d="M100 1820 L1100 1820 L1100 1920 L100 1920 Z" fill="url(#metal-mesh-ultra)" stroke="#555" className="svg-item" />
                        <text x="600" y="1885" textAnchor="middle" fill="#999" fontSize="32" fontWeight="bold">SERVICE CATWALK SYSTEM (B1 SUB-LEVEL)</text>
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

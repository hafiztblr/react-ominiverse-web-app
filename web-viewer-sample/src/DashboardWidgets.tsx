import React from 'react';

// --- Alarm List Component ---

interface Alarm {
    id: string;
    tag: string;
    description: string;
    status: 'critical' | 'warning' | 'info';
}

export const AlarmList: React.FC<{ alarms: Alarm[] }> = ({ alarms }) => (
    <div className="dashboard-widget alarm-list">
        <h3>System Alarms</h3>
        <div className="widget-content">
            {alarms.map(alarm => (
                <div key={alarm.id} className={`alarm-item status-${alarm.status}`}>
                    <div className="alarm-indicator"></div>
                    <div className="alarm-details">
                        <span className="alarm-tag">{alarm.tag}</span>
                        <span className="alarm-desc">{alarm.description}</span>
                    </div>
                </div>
            ))}
            {alarms.length === 0 && <div className="no-alarms">No active alarms</div>}
        </div>
    </div>
);

// --- Asset Summary (Copilot Style) ---

interface AssetSummaryProps {
    name: string;
    type: string;
    summary: string;
    health: number;
}

export const AssetSummary: React.FC<AssetSummaryProps> = ({ name, type, summary, health }) => (
    <div className="dashboard-widget asset-summary">
        <div className="asset-header">
            <h3>{name || 'No Selection'}</h3>
            <span className="asset-type">{type}</span>
        </div>
        <div className="widget-content">
            <div className="health-meter">
                <span>Operational Health</span>
                <div className="meter-track">
                    <div className="meter-fill" style={{ width: `${health}%`, backgroundColor: health > 80 ? '#76b900' : '#f0a500' }}></div>
                </div>
                <span className="health-value">{health}%</span>
            </div>
            <p className="summary-text">{summary}</p>
        </div>
    </div>
);

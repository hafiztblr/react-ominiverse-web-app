import React from 'react';
import SensorChart from './SensorChart';
import { AlarmList, AssetSummary } from './DashboardWidgets';

interface DashboardOverlayProps {
    selectedAsset: {
        name: string;
        path: string;
    } | null;
}

// Mock data generator based on selection
const getMockData = (assetName: string) => {
    if (!assetName) return null;

    // Generic mock data
    const history = Array.from({ length: 10 }, (_, i) => ({
        label: `${i}:00`,
        value: 40 + Math.random() * 40
    }));

    const isMachine = assetName.toLowerCase().includes('robot') || assetName.toLowerCase().includes('machine');
    const isTank = assetName.toLowerCase().includes('tank') || assetName.toLowerCase().includes('container');

    return {
        type: isMachine ? 'Industrial Equipment' : isTank ? 'Storage Vessel' : 'Facility Asset',
        summary: `Digital twin analytics show ${assetName} is performing within optimal parameters. Real-time telemetry indicates stable vibrations and pressure levels.`,
        health: 85 + Math.floor(Math.random() * 15),
        charts: [
            { title: 'Temperature', data: history, unit: '°C' },
            { title: 'Efficiency', data: history.map(d => ({ ...d, value: d.value - 10 })), type: 'bar' as const, unit: '%' }
        ],
        alarms: assetName.includes('Robot') ? [
            { id: '1', tag: 'VIBR_01', description: 'Secondary vibration threshold reached', status: 'warning' as const }
        ] : []
    };
};

const DashboardOverlay: React.FC<DashboardOverlayProps> = ({ selectedAsset }) => {
    const data = getMockData(selectedAsset?.name || '');

    return (
        <div className="dashboard-overlay-container">
            <div className="dashboard-header">
                <h2>Digital Twin Analytics</h2>
                <div className="live-indicator">
                    <div className="pulse"></div> LIVE
                </div>
            </div>

            <div className="dashboard-content">
                <AssetSummary
                    name={selectedAsset?.name || 'Select an Asset'}
                    type={data?.type || 'Waiting for selection...'}
                    summary={data?.summary || 'Click on an object in the 3D viewer to see detailed telemetry and health reports.'}
                    health={data?.health || 0}
                />

                {data && (
                    <>
                        <div className="charts-grid">
                            {data.charts.map((c, i) => (
                                <SensorChart key={i} {...c} type={c.type || 'line'} />
                            ))}
                        </div>
                        <AlarmList alarms={data.alarms} />
                    </>
                )}
            </div>
        </div>
    );
};

export default DashboardOverlay;

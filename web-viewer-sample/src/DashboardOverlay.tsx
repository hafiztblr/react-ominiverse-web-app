import React from 'react';
import SensorChart from './SensorChart';
import { AlarmList, AssetSummary } from './DashboardWidgets';
import { LiveSensorData } from './Window';

interface DashboardOverlayProps {
    selectedAsset: {
        name: string;
        path: string;
    } | null;
    shipYHistory: LiveSensorData[];
    shipZHistory: LiveSensorData[];
}

const DashboardOverlay: React.FC<DashboardOverlayProps> = ({ selectedAsset, shipYHistory, shipZHistory }) => {
    const assetName = selectedAsset?.name || '';
    const isShip = assetName.toLowerCase().includes('ship') || assetName.toLowerCase().includes('boat');

    // Default mock behavior for non-ship assets, but REAL data for the ship
    const charts = isShip ? [
        { title: 'Bobbing (Y)', data: shipYHistory, unit: 'm', color: '#00d2ff' },
        { title: 'Docking Progress (Z)', data: shipZHistory, unit: 'm', color: '#76b900' }
    ] : [
        { title: 'Temperature', data: Array.from({ length: 10 }, (_, i) => ({ label: `${i}s`, value: 40 + Math.random() * 10 })), unit: '°C' },
        { title: 'Efficiency', data: Array.from({ length: 10 }, (_, i) => ({ label: `${i}s`, value: 80 + Math.random() * 5 })), type: 'bar' as const, unit: '%' }
    ];

    const health = isShip ? 98 : (assetName ? 85 : 0);

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
                    name={assetName || 'Select an Asset'}
                    type={isShip ? 'Maritime Vessel' : (assetName ? 'Facility Asset' : 'Waiting for selection...')}
                    summary={isShip ?
                        `Real-time telemetry for ${assetName}. Monitoring hull stability (Y) and docking approach (Z).` :
                        (assetName ? `Monitoring ${assetName} performance. Telemetry indicates stable operations.` : 'Click on an object in the 3D viewer to see detailed telemetry and health reports.')
                    }
                    health={health}
                />

                {assetName && (
                    <>
                        <div className="charts-grid">
                            {charts.map((c, i) => (
                                <SensorChart key={i} {...c} type={(c as any).type || 'line'} />
                            ))}
                        </div>
                        <AlarmList alarms={[]} />
                    </>
                )}
            </div>
        </div>
    );
};

export default DashboardOverlay;

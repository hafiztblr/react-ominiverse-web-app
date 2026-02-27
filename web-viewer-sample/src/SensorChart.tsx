import React from 'react';

interface DataPoint {
    label: string;
    value: number;
}

interface SensorChartProps {
    title: string;
    data: DataPoint[];
    type: 'line' | 'bar';
    color?: string;
    unit?: string;
}

const SensorChart: React.FC<SensorChartProps> = ({ title, data, type, color = '#76b900', unit = '' }) => {
    const width = 300;
    const height = 120;
    const padding = 20;

    const maxVal = Math.max(...data.map(d => d.value), 100);
    const minVal = 0;

    const getX = (index: number) => padding + (index * (width - 2 * padding) / (data.length - 1));
    const getY = (value: number) => height - padding - ((value - minVal) / (maxVal - minVal) * (height - 2 * padding));

    const points = data.map((d, i) => `${getX(i)},${getY(d.value)}`).join(' ');

    return (
        <div className="sensor-chart-widget">
            <div className="chart-header">
                <span className="chart-title">{title}</span>
                <span className="chart-value">{data[data.length - 1]?.value}{unit}</span>
            </div>
            <div className="chart-container">
                <svg width="100%" height={height} viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
                    <defs>
                        <linearGradient id={`grad-${title}`} x1="0%" y1="0%" x2="0%" y2="100%">
                            <stop offset="0%" style={{ stopColor: color, stopOpacity: 0.4 }} />
                            <stop offset="100%" style={{ stopColor: color, stopOpacity: 0 }} />
                        </linearGradient>
                    </defs>

                    {/* Grid Lines */}
                    <line x1={padding} y1={padding} x2={padding} y2={height - padding} stroke="rgba(255,255,255,0.1)" />
                    <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="rgba(255,255,255,0.1)" />

                    {type === 'line' && (
                        <>
                            <path
                                d={`M ${points} L ${getX(data.length - 1)},${height - padding} L ${getX(0)},${height - padding} Z`}
                                fill={`url(#grad-${title})`}
                            />
                            <polyline
                                fill="none"
                                stroke={color}
                                strokeWidth="2"
                                points={points}
                            />
                        </>
                    )}

                    {type === 'bar' && data.map((d, i) => {
                        const x = getX(i) - 5;
                        const y = getY(d.value);
                        const barHeight = (height - padding) - y;
                        return (
                            <rect
                                key={i}
                                x={x}
                                y={y}
                                width="10"
                                height={barHeight}
                                fill={color}
                                opacity={0.8}
                            />
                        );
                    })}
                </svg>
            </div>
        </div>
    );
};

export default SensorChart;

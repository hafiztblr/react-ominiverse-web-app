/*
 * SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
 * SPDX-License-Identifier: LicenseRef-NvidiaProprietary
 */
import React from "react";
import './App.css';
import DummyData from './assets/dummy_data.json';

interface USDPrimType {
    name?: string;
    path: string;
}

interface USDPropertiesProps {
    width: number;
    selectedUSDPrims: Set<USDPrimType>;
}

interface USDPropertiesState {
    externalData: any | null;
    isLoading: boolean;
    error: string | null;
}

export default class USDProperties extends React.Component<USDPropertiesProps, USDPropertiesState> {
    constructor(props: USDPropertiesProps) {
        super(props);
        this.state = {
            externalData: null,
            isLoading: false,
            error: null
        };
    }

    componentDidUpdate(prevProps: USDPropertiesProps) {
        // Detect selection change
        const prevPrims = Array.from(prevProps.selectedUSDPrims);
        const currentPrims = Array.from(this.props.selectedUSDPrims);

        if (currentPrims.length > 0 && (prevPrims.length === 0 || prevPrims[0].path !== currentPrims[0].path)) {
            this.fetchExternalData(currentPrims[0]);
        } else if (currentPrims.length === 0 && prevPrims.length > 0) {
            this.setState({ externalData: null, error: null });
        }
    }

    async fetchExternalData(prim: USDPrimType) {
        this.setState({ isLoading: true, error: null });

        const path = prim.path;
        const uniqueId = path.replace(/\//g, '_');
        const apiUrl = `https://usd-data/${uniqueId}`;

        console.log(`Calling API: ${apiUrl} for path: ${path}`);

        // Simulating the API response by looking up in our dummy_data.json mapping
        setTimeout(() => {
            const dataMap: { [key: string]: any } = DummyData;
            const responseData = dataMap[path];

            if (responseData) {
                this.setState({
                    externalData: responseData,
                    isLoading: false
                });
            } else {
                // Fallback for paths not in our dummy file
                this.setState({
                    externalData: {
                        status: "Unknown",
                        temperature: "N/A",
                        lastMaintenance: "N/A",
                        energyUsage: "N/A",
                        info: "No data mapped for this path"
                    },
                    isLoading: false
                });
            }
        }, 600);
    }

    render() {
        const selectedPrims = Array.from(this.props.selectedUSDPrims);
        const { externalData, isLoading } = this.state;

        if (selectedPrims.length === 0) {
            return null;
        }

        const prim = selectedPrims[0];

        return (
            <div className="usdPropertiesContainer" style={{ width: this.props.width }}>
                <div className="usdPropertiesHeader">
                    {'Object Details'}
                </div>
                <div className="usdPropertiesContent">
                    <div className="property-item">
                        <div className="property-label">Name</div>
                        <div className="property-value">{prim.name}</div>

                        <div className="property-label" style={{ marginTop: '10px' }}>Path</div>
                        <div className="property-value" style={{ fontSize: '10px', wordBreak: 'break-all' }}>{prim.path}</div>
                    </div>

                    <div className="property-section-header">KPIS</div>

                    {isLoading ? (
                        <div className="loading-small">Fetching data from API...</div>
                    ) : externalData ? (
                        <div className="external-data-grid">
                            <div className="data-row">
                                <span className="data-label">Status:</span>
                                <span className="data-value status-ok">{externalData.status}</span>
                            </div>
                            <div className="data-row">
                                <span className="data-label">Temp:</span>
                                <span className="data-value">{externalData.temperature}</span>
                            </div>
                            <div className="data-row">
                                <span className="data-label">Power:</span>
                                <span className="data-value">{externalData.energyUsage}</span>
                            </div>
                        </div>
                    ) : (
                        <div className="data-placeholder">No external data linked.</div>
                    )}

                    <div className="property-section-header">Transform</div>
                    <div className="transform-grid">
                        <div className="transform-row">
                            <span>T</span>
                            <span>0.0</span><span>0.0</span><span>0.0</span>
                        </div>
                        <div className="transform-row">
                            <span>R</span>
                            <span>0.0</span><span>0.0</span><span>0.0</span>
                        </div>
                        <div className="transform-row">
                            <span>S</span>
                            <span>1.0</span><span>1.0</span><span>1.0</span>
                        </div>
                    </div>
                </div>
            </div>
        );
    }
}

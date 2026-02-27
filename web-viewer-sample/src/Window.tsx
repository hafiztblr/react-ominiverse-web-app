/*
 * SPDX-FileCopyrightText: Copyright (c) 2024 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
 * SPDX-License-Identifier: LicenseRef-NvidiaProprietary
 *
 * NVIDIA CORPORATION, its affiliates and licensors retain all intellectual
 * property and proprietary rights in and to this material, related
 * documentation and any modifications thereto. Any use, reproduction,
 * disclosure or distribution of this material and related documentation
 * without an express license agreement from NVIDIA CORPORATION or
 * its affiliates is strictly prohibited.
 */
import React from 'react';
import './App.css';
import AppStream from './AppStream';
import StreamConfig from '../stream.config.json';
import USDProperties from "./USDProperties";
import { headerHeight } from './App';
import entityMapping from './assets/entity_mapping.json';
import SVGSelectionPanel from './svg/SVGSelectionPanel';


interface USDAssetType {
    name: string;
    url: string;
}

interface USDPrimType {
    name?: string;
    path: string;
    children?: USDPrimType[];
}

export interface AppProps {
    sessionId: string
    backendUrl: string
    signalingserver: string
    signalingport: number
    mediaserver: string
    mediaport: number
    accessToken: string
    onStreamFailed: () => void;
}

interface AppState {
    usdAssets: USDAssetType[];
    selectedUSDAsset: USDAssetType;
    usdPrims: USDPrimType[];
    selectedUSDPrims: Set<USDPrimType>;
    isKitReady: boolean;
    showStream: boolean;
    showUI: boolean;
    isLoading: boolean;
    loadingText: string;
    pendingFocusId: string | null;
    progress: number;
    displayProgress: number;
    selectedSVGId: string | null;
    animationState: 'stopped' | 'playing' | 'paused';
}

interface AppStreamMessageType {
    event_type: string;
    payload: any;
}

export default class App extends React.Component<AppProps, AppState> {

    private _progressInterval: any = null;
    // private _streamConfig: StreamConfigType = getConfig();

    constructor(props: AppProps) {
        super(props);

        // list of selectable USD assets
        const usdAssets: USDAssetType[] = [
            { name: "Factory", url: "C:/Users/USER/Desktop/Hafiz/Omiverse/web-app/kit-app-template/source/examples/Factory.usd" },
            { name: "Boat", url: "C:/Users/USER/Desktop/Hafiz/Omiverse/web-app/kit-app-template/source/examples/Boat.usd" },
        ];

        this.state = {
            usdAssets: usdAssets,
            selectedUSDAsset: usdAssets[0],
            usdPrims: [],
            selectedUSDPrims: new Set<USDPrimType>(),
            isKitReady: false,
            showStream: false,
            showUI: false,
            loadingText: StreamConfig.source === "gfn" ? "Log in to GeForce NOW to view stream" : (StreamConfig.source === "stream" ? "Waiting for stream to initialize" : "Waiting for stream to begin"),
            isLoading: true,
            pendingFocusId: new URLSearchParams(window.location.search).get('focus'),
            progress: 0,
            displayProgress: 0,
            selectedSVGId: null,
            animationState: 'stopped',
        }
    }

    componentDidMount() {
        console.info("Window component mounted.");
        // Start simulation immediately if stream isn't shown yet
        if (!this.state.showStream) {
            console.info("Starting robust progress simulation...");
            this._startProgressSimulation();
        }
    }

    componentWillUnmount() {
        this._stopProgressSimulation();
    }

    private _handleSVGSelect = (id: string) => {
        console.log(`DASHBOARD: 2D Selection triggered for ID: ${id}`);
        this.setState({ selectedSVGId: id });

        const mapping: { [key: string]: string } = entityMapping;
        const usdPath = mapping[id];

        if (usdPath) {
            // Instant feedback: Hide any old loaders and move camera
            this._stopProgressSimulation();
            this._selectAndFrame(usdPath);
        }
    }

    private _startProgressSimulation() {
        this._stopProgressSimulation(); // Clear any existing
        this.setState({ displayProgress: 0, progress: 0 });

        this._progressInterval = setInterval(() => {
            if (this.state.showStream) {
                console.log("Stream ready, stopping simulation.");
                this._stopProgressSimulation();
                return;
            }
            this.setState(prevState => {
                const { progress, displayProgress } = prevState;
                // If real progress is ahead, jump to it
                if (progress > displayProgress) {
                    return { displayProgress: progress };
                }
                // Slow down as we reach the end if no real progress
                const increment = displayProgress < 90 ? 0.8 : 0.1;
                const nextProgress = Math.min(99, displayProgress + increment);
                console.log(`Simulating progress: ${nextProgress.toFixed(1)}%`);
                return { displayProgress: Number(nextProgress.toFixed(1)) };
            });
        }, 200); // Update every 200ms to be less intensive
    }

    private _stopProgressSimulation() {
        if (this._progressInterval) {
            clearInterval(this._progressInterval);
            this._progressInterval = null;
        }
    }

    /**
    * @function _queryLoadingState
    *
    * Sends Kit a message to find out what the loading state is.
    * Receives a 'loadingStateResponse' event type
    */
    private _queryLoadingState(): void {
        const message: AppStreamMessageType = {
            event_type: "loadingStateQuery",
            payload: {}
        };
        AppStream.sendMessage(JSON.stringify(message));
    }

    /**
     * @function _onStreamStarted
     *
     * Sends a request to open an asset. If the stream is from GDN it is assumed that the
     * application will automatically load an asset on startup so a request to open a stage
     * is not sent. Instead, we wait for the streamed application to send a
     * openedStageResult message.
     */
    private _onStreamStarted(): void {
        this._pollForKitReady()
    }

    /**
    * @function _pollForKitReady
    *
    * Attempts to query Kit's loading state until a response is received.
    * Once received, the 'isKitReady' flag is set to true and polling ends
    */
    async _pollForKitReady() {
        if (this.state.isKitReady === true) return

        console.info("polling Kit availability")
        this._queryLoadingState()

        // After polling, check if we need to focus an object from the URL
        this._checkInitialFocus();

        setTimeout(() => this._pollForKitReady(), 3000); // Poll every 3 seconds
    }

    private _checkInitialFocus(): void {
        const focusId = this.state.pendingFocusId;
        if (focusId && this.state.isKitReady) {
            const mapping: { [key: string]: string } = entityMapping;
            const usdPath = mapping[focusId];
            if (usdPath) {
                console.log(`Checking if we can focus on: ${usdPath}`);
                // Only execute if we have enough info or wait for children
                this._selectAndFrame(usdPath);
            }
        }
    }

    private _selectAndFrame(path: string): void {
        console.log(`Executing focus/frame for: ${path}`);

        // 1. Select the prim in Kit
        const selectMessage: AppStreamMessageType = {
            event_type: "selectPrimsRequest",
            payload: {
                paths: [path]
            }
        };
        AppStream.sendMessage(JSON.stringify(selectMessage));

        // 2. Update local UI state
        // Try to find the prim in our tree, or create a skeleton so the property panel updates
        let usdPrim = this._findUSDPrimByPath(path);
        if (!usdPrim) {
            console.warn(`Prim ${path} not found in UI tree, creating skeleton for details panel.`);
            const name = path.split('/').pop() || path;
            usdPrim = { name, path };
        }

        this.setState({ selectedUSDPrims: new Set([usdPrim]) });

        // 3. Frame the prim (Focus) - slightly delayed to allow selection to register
        setTimeout(() => {
            console.log(`Sending frameSelection for: ${path}`);
            const frameMessage: AppStreamMessageType = {
                event_type: "frameSelection",
                payload: {}
            };
            AppStream.sendMessage(JSON.stringify(frameMessage));
        }, 1500); // Increased delay for larger Factory scene stability
    }

    /**
     * @function _getAsset
     * 
     * Attempts to retrieve an asset from the list of USD assets based on a supplied USD path
     * If a match is not found, a USDAssetType with empty values is returned.
     */
    private _getAsset(path: string): USDAssetType {
        if (!path)
            return { name: "", url: "" }

        // returns the file name from a path
        const getFileNameFromPath = (path: string): string | undefined => path.split(/[/\\]/).pop();

        for (const asset of this.state.usdAssets) {
            if (getFileNameFromPath(asset.url) === getFileNameFromPath(path))
                return asset
        }

        return { name: "", url: "" }
    }

    /**
    * @function _onLoggedIn
    *
    * Runs when the user logs in
    */
    private _onLoggedIn(userId: string): void {
        if (StreamConfig.source === "gfn") {
            console.info(`Logged in to GeForce NOW as ${userId}`)
            this.setState({ loadingText: "Waiting for stream to begin", isLoading: false })
        }
    }

    /**
    * @function _openSelectedAsset
    *
    * Send a request to load an asset based on the currently selected asset
    */
    private _openSelectedAsset(): void {
        this._startProgressSimulation();
        this.setState({ loadingText: "Loading Asset...", showStream: false, isLoading: true })
        this.setState({ usdPrims: [], selectedUSDPrims: new Set<USDPrimType>() });
        console.log(`Sending request to open asset: ${this.state.selectedUSDAsset.url}.`);
        const message: AppStreamMessageType = {
            event_type: "openStageRequest",
            payload: {
                url: this.state.selectedUSDAsset.url
            }
        };
        AppStream.sendMessage(JSON.stringify(message));
    }

    /**
    * @function _getChildren
    *
    * Send a request for the child prims of the given usdPrim.
    * Note that a filter is supported.
    */
    private _getChildren(usdPrim: USDPrimType | null = null): void {
        // Get geometry prims. If no usdPrim is specified then get children of /World.
        console.log(`Requesting children for path: ${usdPrim ? usdPrim.path : '/World'}.`);
        const message: AppStreamMessageType = {
            event_type: "getChildrenRequest",
            payload: {
                prim_path: usdPrim ? usdPrim.path : '/World',
                filters: ['USDGeom']
            }
        };
        AppStream.sendMessage(JSON.stringify(message));
    }

    /**
    * @function _makePickable
    *
    * Send a request to make prims pickable/selectable.
    * By default the client requests to make only a handful of the prims selectable - leaving the background items unselectable.
    */
    private _makePickable(usdPrims: USDPrimType[]): void {
        const paths: string[] = usdPrims.map(prim => prim.path);
        console.log(`Sending request to make prims pickable: ${paths}.`);
        const message: AppStreamMessageType = {
            event_type: "makePrimsPickable",
            payload: {
                paths: paths,
            }
        };
        AppStream.sendMessage(JSON.stringify(message));
    }

    /**
    * @function _onFillUSDPrim
    *
    * If the usdPrim has a children property a request is sent for its children.
    */
    private _onFillUSDPrim(usdPrim: USDPrimType): void {
        if (usdPrim !== null && "children" in usdPrim && !Array.isArray(usdPrim.children)) {
            this._getChildren(usdPrim);
        }
    }

    /**
    * @function _onStageReset
    *
    * Clears the selection and sends a request to reset the stage to how it was at the time it loaded.
    */
    private _onStageReset(): void {
        console.log("DASHBOARD: Reset Stage triggered.");
        this.setState({ selectedUSDPrims: new Set<USDPrimType>() });

        // 1. Clear selection in Kit
        const selection_message: AppStreamMessageType = {
            event_type: "selectPrimsRequest",
            payload: {
                paths: []
            }
        };
        AppStream.sendMessage(JSON.stringify(selection_message));

        // 2. Clear SVG selection
        this.setState({ selectedSVGId: null });

        // 3. Reset Stage in Kit
        const reset_message: AppStreamMessageType = {
            event_type: "resetStage",
            payload: {}
        };
        AppStream.sendMessage(JSON.stringify(reset_message));
        this.setState({ animationState: 'stopped' });
    }

    /**
    * @function _onPlayAnimation
    *
    * Sends a 'playAnimation' message to the Kit extension to start / resume the USD timeline.
    */
    private _onPlayAnimation(): void {
        const msg: AppStreamMessageType = { event_type: "playAnimation", payload: {} };
        AppStream.sendMessage(JSON.stringify(msg));
        this.setState({ animationState: 'playing' });
    }

    /**
    * @function _onPauseAnimation
    *
    * Sends a 'pauseAnimation' message to the Kit extension to pause the USD timeline.
    */
    private _onPauseAnimation(): void {
        const msg: AppStreamMessageType = { event_type: "pauseAnimation", payload: {} };
        AppStream.sendMessage(JSON.stringify(msg));
        this.setState({ animationState: 'paused' });
    }

    /**
    * @function _onStopAnimation
    *
    * Sends a 'stopAnimation' message to the Kit extension to stop and reset the USD timeline.
    */
    private _onStopAnimation(): void {
        const msg: AppStreamMessageType = { event_type: "stopAnimation", payload: {} };
        AppStream.sendMessage(JSON.stringify(msg));
        this.setState({ animationState: 'stopped' });
    }


    /**
    * @function _findUSDPrimByPath
    *
    * Recursive search for a USDPrimType object by path.
    */
    private _findUSDPrimByPath(path: string, array: USDPrimType[] = this.state.usdPrims): USDPrimType | null {
        if (Array.isArray(array)) {
            for (const obj of array) {
                if (obj.path === path) {
                    return obj;
                }
                if (obj.children && obj.children.length > 0) {
                    const found = this._findUSDPrimByPath(path, obj.children);
                    if (found) {
                        return found;
                    }
                }
            }
        }
        return null;
    }

    /**
    * @function _handleCustomEvent
    *
    * Handle message from stream.
    */
    private _handleCustomEvent(event: any): void {
        if (!event) {
            return;
        }

        // response received once a USD asset is fully loaded
        if (event.event_type === "openedStageResult") {
            if (event.payload.result === "success") {
                this._queryLoadingState()
            }
            else {
                console.error('Kit App communicates there was an error loading: ' + event.payload.url);
            }
        }

        // response received from the 'loadingStateQuery' request
        else if (event.event_type == "loadingStateResponse") {
            // loadingStateRequest is used to poll Kit for proof of life.
            // For the first loadingStateResponse we set isKitReady to true
            // and run one more query to find out what the current loading state
            // is in Kit
            if (this.state.isKitReady === false) {
                console.info("Kit is ready to load assets")
                this.setState({ isKitReady: true })
                this._queryLoadingState()
            }

            else {
                const usdAsset: USDAssetType = this._getAsset(event.payload.url)
                const isStageValid: boolean = !!(usdAsset.name && usdAsset.url)

                // set the USD Asset dropdown to the currently opened stage if it doesn't match
                if (isStageValid && usdAsset !== undefined && this.state.selectedUSDAsset !== usdAsset)
                    this.setState({ selectedUSDAsset: usdAsset })

                // if the stage is empty, force-load the selected usd asset; the loading state is irrelevant
                if (!event.payload.url)
                    this._openSelectedAsset()

                // if a stage has been fully loaded and isn't a part of this application, force-load the selected stage
                else if (!isStageValid && event.payload.loading_state === "idle") {
                    console.log(`The loaded asset ${event.payload.url} is invalid.`)
                    this._openSelectedAsset()
                }

                // show stream and populate children if the stage is valid and it's done loading
                if (isStageValid && event.payload.loading_state === "idle") {
                    this._stopProgressSimulation();
                    this.setState({ displayProgress: 100, showStream: true, loadingText: "Asset loaded", showUI: true, isLoading: false })
                    this._getChildren()
                }
            }
        }

        // Loading progress amount notification.
        else if (event.event_type === "updateProgressAmount") {
            const progress = Math.round(event.payload.amount * 100);
            console.log(`Kit App communicates progress: ${progress}%`);
            this.setState({ progress });
        }

        // Loading activity notification.
        else if (event.event_type === "updateProgressActivity") {
            console.log('Kit App communicates progress activity.');
            if (this.state.loadingText !== "Loading Asset...")
                this.setState({ loadingText: "Loading Asset...", isLoading: true })
        }

        // Notification from Kit about user changing the selection via the viewport.
        else if (event.event_type === "stageSelectionChanged") {
            console.log(event.payload.prims.constructor.name);
            if (!Array.isArray(event.payload.prims) || event.payload.prims.length === 0) {
                console.log('Kit App communicates an empty stage selection.');
                this.setState({ selectedUSDPrims: new Set<USDPrimType>() });
            }
            else {
                console.log('Kit App communicates selection of a USDPrimType: ' + event.payload.prims.map((obj: any) => obj).join(', '));
                const usdPrimsToSelect: Set<USDPrimType> = new Set<USDPrimType>();
                event.payload.prims.forEach((obj: any) => {
                    const result = this._findUSDPrimByPath(obj);
                    if (result !== null) {
                        usdPrimsToSelect.add(result);
                    }
                });
                this.setState({ selectedUSDPrims: usdPrimsToSelect });
            }
        }
        // Streamed app provides children of a parent USDPrimType
        else if (event.event_type === "getChildrenResponse") {
            console.log('Kit App sent stage prims');
            const prim_path = event.payload.prim_path;
            const children = event.payload.children;
            const usdPrim = this._findUSDPrimByPath(prim_path);
            if (usdPrim === null) {
                this.setState({ usdPrims: children });
            }
            else {
                usdPrim.children = children;
                this.setState({ usdPrims: this.state.usdPrims });
            }
            if (Array.isArray(children)) {
                this._makePickable(children);
            }

            // Check if we have a pending focus that matches one of these children
            if (this.state.pendingFocusId) {
                const mapping: { [key: string]: string } = entityMapping;
                const targetPath = mapping[this.state.pendingFocusId];
                if (targetPath) {
                    const foundInThisBatch = children?.some((c: any) => c.path === targetPath) ||
                        this._findUSDPrimByPath(targetPath);
                    if (foundInThisBatch) {
                        console.log(`Target path ${targetPath} found. Executing focus.`);
                        this._selectAndFrame(targetPath);
                        this.setState({ pendingFocusId: null }); // Clear once handled
                    }
                }
            }
        }
        // other messages from app to kit
        else if (event.messageRecipient === "kit") {
            console.log("onCustomEvent");
            console.log(JSON.parse(event.data).event_type);
        }
    }

    /**
    * @function _handleAppStreamFocus
    *
    * Update state when AppStream is in focus.
    */
    private _handleAppStreamFocus(): void {
        console.log('User is interacting in streamed viewer');
    }

    /**
    * @function _handleAppStreamBlur
    *
    * Update state when AppStream is not in focus.
    */
    private _handleAppStreamBlur(): void {
        console.log('User is not interacting in streamed viewer');
    }

    render() {
        return (
            <div
                className="dashboard-container"
                style={{
                    position: 'absolute',
                    top: headerHeight,
                    width: '100%',
                    height: `calc(100% - ${headerHeight}px)`,
                    overflow: 'hidden'
                }}
            >
                {/* Left Sidebar: 2D SVG Selection */}
                <SVGSelectionPanel
                    onSelect={this._handleSVGSelect}
                    selectedId={this.state.selectedSVGId}
                />

                {/* Right Side: Main Viewer Content */}
                <div className="main-viewer-content">
                    {/* Full-Screen Streamed app */}
                    <div style={{
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        width: '100%',
                        height: '100%',
                        zIndex: 1
                    }}>
                        {!this.state.showStream &&
                            <div className="loading-container">
                                <div className="progress-percentage">{Math.floor(this.state.displayProgress)}%</div>
                                <div className="loading-text">{this.state.loadingText}</div>
                                <div className="progress-bar-container">
                                    <div
                                        className="progress-bar-fill"
                                        style={{ width: `${this.state.displayProgress}%` }}
                                    />
                                </div>
                            </div>
                        }

                        <AppStream
                            sessionId={this.props.sessionId}
                            backendUrl={this.props.backendUrl}
                            signalingserver={this.props.signalingserver}
                            signalingport={this.props.signalingport}
                            mediaserver={this.props.mediaserver}
                            mediaport={this.props.mediaport}
                            accessToken={this.props.accessToken}
                            onStarted={() => this._onStreamStarted()}
                            onFocus={() => this._handleAppStreamFocus()}
                            onBlur={() => this._handleAppStreamBlur()}
                            style={{
                                width: '100%',
                                height: '100%',
                                visibility: this.state.showStream ? 'visible' : 'hidden'
                            }}
                            onLoggedIn={(userId) => this._onLoggedIn(userId)}
                            handleCustomEvent={(event) => this._handleCustomEvent(event)}
                            onStreamFailed={this.props.onStreamFailed}
                        />
                    </div>

                    {/* Bottom Center Controls */}
                    {this.state.showStream && (
                        <div className="bottom-center-controls">
                            {/* Play / Pause toggle */}
                            {this.state.animationState !== 'playing' ? (
                                <button
                                    className="anim-control-button play-button"
                                    onClick={() => this._onPlayAnimation()}
                                    title="Play Animation"
                                >
                                    ▶ Play
                                </button>
                            ) : (
                                <button
                                    className="anim-control-button pause-button"
                                    onClick={() => this._onPauseAnimation()}
                                    title="Pause Animation"
                                >
                                    ⏸ Pause
                                </button>
                            )}
                            {/* Stop button — only shown when playing or paused */}
                            {this.state.animationState !== 'stopped' && (
                                <button
                                    className="anim-control-button stop-button"
                                    onClick={() => this._onStopAnimation()}
                                    title="Stop Animation"
                                >
                                    ⏹ Stop
                                </button>
                            )}
                            <button
                                className="reset-scene-button"
                                onClick={() => this._onStageReset()}
                                title="Reset Scene"
                            >
                                ↺ Reset Scene
                            </button>
                        </div>
                    )}

                    {/* Floating Immersive Overlay (Now relative to viewer only) */}
                    {this.state.showUI &&
                        <div className="immersive-overlay">
                            {/* Removed USDStage per user request */}
                            <USDProperties
                                width={300}
                                selectedUSDPrims={this.state.selectedUSDPrims}
                            />
                        </div>
                    }
                </div>
            </div>
        );
    }
}

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
import React, { Component } from 'react';
import PropTypes from 'prop-types';
import { AppStreamer, StreamEvent, StreamProps, DirectConfig, GFNConfig, StreamType, LogLevel } from '@nvidia/omniverse-webrtc-streaming-library';
import StreamConfig from '../stream.config.json';


interface AppStreamProps {
    sessionId: string
    backendUrl: string
    signalingserver: string
    signalingport: number
    mediaserver: string
    mediaport: number
    accessToken: string
    style?: React.CSSProperties;
    onStarted: () => void;
    onStreamFailed: () => void;
    onLoggedIn: (userId: string) => void;
    handleCustomEvent: (event: any) => void;
    onFocus: () => void;
    onBlur: () => void;
    onPointerHover: (x: number, y: number, normalizedX: number, normalizedY: number, visible: boolean) => void;
}

interface AppStreamState {
    streamReady: boolean;
}

export default class AppStream extends Component<AppStreamProps, AppStreamState> {
    private _requested: boolean;
    private _orbiting = false;
    private _orbitPointerId: number | null = null;
    private _orbitX = 0;
    private _orbitY = 0;

    static defaultProps = {
        style: {}
    };

    static propTypes = {
        onStarted: PropTypes.func.isRequired,
        handleCustomEvent: PropTypes.func.isRequired,
        style: PropTypes.object
    };

    constructor(props: AppStreamProps) {
        super(props);

        this._requested = false;
        this.state = {
            streamReady: false
        };
    }

    componentDidMount() {
        if (!this._requested) {
            this._requested = true;

            let streamProps: StreamProps;
            let streamConfig: DirectConfig | GFNConfig;
            let streamSource: StreamType.DIRECT | StreamType.GFN;

            if (StreamConfig.source === 'gfn') {
                streamSource = StreamType.GFN;
                streamConfig = {
                    //@ts-ignore
                    GFN: GFN,
                    catalogClientId: StreamConfig.gfn.catalogClientId,
                    clientId: StreamConfig.gfn.clientId,
                    cmsId: StreamConfig.gfn.cmsId,
                    onUpdate: (message: StreamEvent) => this._onUpdate(message),
                    onStart: (message: StreamEvent) => this._onStart(message),
                    onCustomEvent: (message: any) => this._onCustomEvent(message)
                }
            }

            else if (StreamConfig.source === 'local') {
                streamSource = StreamType.DIRECT;
                streamConfig = {
                    videoElementId: 'remote-video',
                    audioElementId: 'remote-audio',
                    authenticate: false,
                    maxReconnects: 20,
                    signalingServer: StreamConfig.local.server,
                    signalingPort: StreamConfig.local.signalingPort,
                    mediaServer: StreamConfig.local.server,
                    ...(StreamConfig.local.mediaPort != null && { mediaPort: StreamConfig.local.mediaPort }),
                    nativeTouchEvents: true,
                    width: 1280,
                    height: 720,
                    fps: 30,
                    onUpdate: (message: StreamEvent) => this._onUpdate(message),
                    onStart: (message: StreamEvent) => this._onStart(message),
                    onCustomEvent: (message: any) => this._onCustomEvent(message),
                    onStop: (_message: StreamEvent) => { /* no-op */ },
                    onTerminate: (_message: StreamEvent) => { /* no-op */ }
                };
            }

            else if (StreamConfig.source === 'stream') {
                streamSource = StreamType.DIRECT;
                streamConfig = {
                    signalingServer: this.props.signalingserver,
                    signalingPort: this.props.signalingport,
                    mediaServer: this.props.mediaserver,
                    mediaPort: this.props.mediaport,
                    backendUrl: this.props.backendUrl,
                    sessionId: this.props.sessionId,
                    autoLaunch: true,
                    cursor: 'free',
                    mic: false,
                    videoElementId: 'remote-video',
                    audioElementId: 'remote-audio',
                    authenticate: false,
                    maxReconnects: 20,
                    nativeTouchEvents: true,
                    width: 1280,
                    height: 720,
                    fps: 30,
                    onUpdate: (message: StreamEvent) => this._onUpdate(message),
                    onStart: (message: StreamEvent) => this._onStart(message),
                    onCustomEvent: (message: any) => this._onCustomEvent(message),
                    onStop: (_message: StreamEvent) => { /* no-op */ },
                    onTerminate: (_message: StreamEvent) => { /* no-op */ },
                };
            }

            else {
                console.error({ message:  StreamConfig});
                return
            }

            try {
                streamProps = { streamConfig, streamSource, logLevel: LogLevel.ERROR }
                AppStreamer.connect(streamProps)
                    .then((result: StreamEvent) => {
                        // use debug sliders in the browser console only if needed
                        // console.info(result);
                    })
                    .catch((error: StreamEvent) => {
                        console.error(error);
                    });
            }
            catch (error) {
                console.error(error);
            }
        }
    }

    componentDidUpdate(_prevProps: AppStreamProps, prevState: AppStreamState, _snapshot: any) {
        if (prevState.streamReady === false && this.state.streamReady === true) {
            const player = document.getElementById("gfn-stream-player-video") as HTMLVideoElement;
            if (player) {
                player.tabIndex = -1;
                player.playsInline = true;
                player.muted = true;
                player.play();
            }
        }
    }

    static sendMessage(message: any) {
        AppStreamer.sendMessage(message);
    }

    static stop() {
        AppStreamer.stop();
        (AppStreamer as any)._stream = null; // Accessing a private member
    }

    private _onOrbitStart = (event: React.PointerEvent<HTMLDivElement>) => {
        if (event.button !== 0) return;
        this._orbiting = true;
        this._orbitPointerId = event.pointerId;
        this._orbitX = event.clientX;
        this._orbitY = event.clientY;
        event.currentTarget.setPointerCapture(event.pointerId);
        event.currentTarget.style.cursor = 'grabbing';
        event.currentTarget.focus();
        event.preventDefault();
        event.stopPropagation();
    };

    private _onOrbitMove = (event: React.PointerEvent<HTMLDivElement>) => {
        const bounds = event.currentTarget.getBoundingClientRect();
        this.props.onPointerHover(
            event.clientX,
            event.clientY,
            (event.clientX - bounds.left) / bounds.width,
            (event.clientY - bounds.top) / bounds.height,
            true,
        );
        if (!this._orbiting || event.pointerId !== this._orbitPointerId) return;
        const deltaX = event.clientX - this._orbitX;
        const deltaY = event.clientY - this._orbitY;
        this._orbitX = event.clientX;
        this._orbitY = event.clientY;
        if (deltaX || deltaY) {
            AppStream.sendMessage(JSON.stringify({
                event_type: 'orbitCamera',
                payload: { deltaX, deltaY },
            }));
        }
        event.preventDefault();
        event.stopPropagation();
    };

    private _onPointerLeave = () => {
        if (!this._orbiting) this.props.onPointerHover(0, 0, 0, 0, false);
    };

    private _onOrbitEnd = (event: React.PointerEvent<HTMLDivElement>) => {
        if (event.pointerId !== this._orbitPointerId) return;
        this._orbiting = false;
        this._orbitPointerId = null;
        event.currentTarget.style.cursor = 'grab';
        if (event.currentTarget.hasPointerCapture(event.pointerId)) {
            event.currentTarget.releasePointerCapture(event.pointerId);
        }
        event.preventDefault();
        event.stopPropagation();
    };

    _onStart(message: any) {
        if (message.action === 'start' && message.status === 'success' && !this.state.streamReady) {
            console.info('streamReady');
            this.setState({ streamReady: true });
            this.props.onStarted();
        }

        if (message.status === "error" && StreamConfig.source === "stream") {
            // console.log(message.info);
            alert(message.info);
            this.props.onStreamFailed();
            return;
        }
    }

    _onUpdate(message: any) {
        try {
            if (message.action === 'authUser' && message.status === 'success') {
                this.props.onLoggedIn(message.info);
            }
        } catch (error) {
            console.error(message);
        }
    }

    _onCustomEvent(message: any) {
        this.props.handleCustomEvent(message);
    }

    _onStop(message: any) {
        console.info('Stream stopped', message);
    }

    _onTerminate(message: any) {
        console.info('Stream terminated', message);
    }

    render() {
        const source = StreamConfig.source;

        if (source === 'local' || source === 'stream') {
            return (
                <div
                    id="main-div"
                    tabIndex={0}
                    onFocus={this.props.onFocus}
                    onBlur={this.props.onBlur}
                    onPointerDownCapture={this._onOrbitStart}
                    onPointerMoveCapture={this._onOrbitMove}
                    onPointerUpCapture={this._onOrbitEnd}
                    onPointerCancelCapture={this._onOrbitEnd}
                    onPointerLeave={this._onPointerLeave}
                    style={{
                        backgroundColor: '#0d1418',
                        cursor: this._orbiting ? 'grabbing' : 'grab',
                        touchAction: 'none',
                        outline: 'none',
                        visibility: this.state.streamReady ? 'visible' : 'hidden',
                        ...this.props.style
                    }}
                >
                    <video
                        id="remote-video"
                        tabIndex={-1}
                        style={{
                            width: '100%',
                            height: '100%',
                        }}
                        playsInline
                        muted
                    />
                    <audio id="remote-audio" muted></audio>
                </div>
            );
        }

        return null;
    }

}

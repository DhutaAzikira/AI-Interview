// Version: FastAPI with HeyGen Connected

// --- 1. CONFIGURATION & STATE ---
let isUserTurn = false;
let gladiaSocket = null;
let controlSocket = null;
let audioProcessor = {};
let sessionId = null;
let interviewTimer = null;
let isAvatarReady = false; // Add this new flag

// HeyGen State
let heygenSessionInfo = null;
let heygenRoom = null;
let heygenMediaStream = null;
let heygenSessionToken = null;


// --- DOM REFERENCES ---
const startFormContainer = document.getElementById('start-form');
const userDetailsForm = document.getElementById('user-details-form');
const chatContainer = document.querySelector('.chat-container');
const endScreen = document.getElementById('end-screen');
const chatLog = document.getElementById('chat-log');
const statusText = document.getElementById('status-text');
const avatarVideo = document.getElementById('avatar-video');
const avatarPlaceholder = document.getElementById('avatar-placeholder');
const avatarStatus = document.getElementById('avatar-status');
const userCamVideo = document.getElementById('user-cam');
const timerDisplay = document.getElementById('timer');

// --- 2. INITIALIZATION & DJANGO BACKEND COMMUNICATION ---
function init() {
    userDetailsForm.addEventListener('submit', startInterview);
}

async function startInterview(event) {
    event.preventDefault();
    const formData = new FormData(userDetailsForm);
    const fullName = formData.get('fullName');
    const email = formData.get('email');
    const booking_code = formData.get('booking_code');

    console.log(`LOG: Starting interview with fullName=${fullName}, email=${email}, booking_code=${booking_code}`);
    if (!fullName || !email) {
        alert('Please fill out all fields.');
        return;
    }

    await startGladiaConnection();

    startFormContainer.style.display = 'none';
    chatContainer.style.display = 'flex';

    try {
        console.log("LOG: Starting interview process...");
        statusText.innerText = "Initializing session with server...";

        initializeUserCamera();
        startInterviewTimer(10);

        const response = await fetch('/api/interview/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ fullName, email, booking_code })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Failed to start interview session.');
        }
        const data = await response.json();
        sessionId = data.sessionId;
        console.log(`LOG: Session ID received: ${sessionId}`);

        // connectToBackendControlSocket();

        // This is now UNCOMMENTED to activate the avatar
        // await initializeHeyGenAvatar();

        await startGladiaConnection();

        statusText.innerText = "Waiting for first question...";
        console.log("LOG: Initial setup complete. Waiting for first question from backend.");

    } catch (error) {
        console.error("Error starting interview:", error);
        statusText.innerText = `Error: ${error.message}`;
        updateAvatarStatus('disconnected', 'Connection Failed');
    }
}

function endInterview() {
    console.log("LOG: Ending the interview.");
    clearInterval(interviewTimer);
    stopGladiaConnection();
    closeHeyGenSession();
    chatContainer.style.display = 'none';
    endScreen.style.display = 'block';
}

// --- 3. HEYGEN AVATAR INTEGRATION (PROXIED) ---

function updateAvatarStatus(status, message) {
    avatarStatus.className = `avatar-status ${status}`;
    avatarStatus.textContent = message;
}

async function getHeyGenSessionToken() {
    // Call our backend proxy
    const response = await fetch(`/api/heygen/create_token`, { method: "POST" });
    if (!response.ok) {
         const errorData = await response.json();
         throw new Error(`Failed to get HeyGen token: ${errorData.message || response.statusText}`);
    }
    const data = await response.json();
    heygenSessionToken = data.data.token;
    console.log("LOG: HeyGen session token obtained via proxy");
}

async function createHeyGenSession() {
    if (!heygenSessionToken) {
        await getHeyGenSessionToken();
    }
    // Call our backend proxy
    const response = await fetch(`/api/heygen/new_session`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: heygenSessionToken }),
    });

    if (!response.ok) {
         const errorData = await response.json();
         throw new Error(`Failed to create HeyGen session: ${errorData.message || response.statusText}`);
    }
    const data = await response.json();
    if (!data.data || !data.data.url) {
        throw new Error("HeyGen session data is invalid.");
    }
    heygenSessionInfo = data.data;

    heygenRoom = new LivekitClient.Room({ adaptiveStream: true, dynacast: true });
    heygenMediaStream = new MediaStream();

    heygenRoom.on(LivekitClient.RoomEvent.TrackSubscribed, (track) => {
        if (track.kind === "video" || track.kind === "audio") {
            heygenMediaStream.addTrack(track.mediaStreamTrack);
            if (heygenMediaStream.getVideoTracks().length > 0) {
                avatarVideo.srcObject = heygenMediaStream;
                avatarVideo.style.display = 'block';
                avatarPlaceholder.style.display = 'none';
                updateAvatarStatus('connected', 'Avatar Ready');
                console.log("HeyGen avatar media stream ready");
                isAvatarReady = true; // <<< SET THE FLAG TO TRUE HERE
                avatarVideo.play().catch(e => console.error("Avatar video play failed:", e));
            }
        }
    });

    heygenRoom.on(LivekitClient.RoomEvent.Disconnected, (reason) => {
        console.log(`HeyGen room disconnected: ${reason}`);
        updateAvatarStatus('disconnected', 'Avatar Disconnected');
    });

    await heygenRoom.prepareConnection(heygenSessionInfo.url, heygenSessionInfo.access_token);
    console.log("LOG: HeyGen session created successfully via proxy");
}

async function startHeyGenStreamingSession() {
    // Call our backend proxy
    await fetch(`/api/heygen/start_session`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            token: heygenSessionToken,
            session_id: heygenSessionInfo.session_id,
        }),
    });
    await heygenRoom.connect(heygenSessionInfo.url, heygenSessionInfo.access_token);
    console.log("LOG: HeyGen streaming started successfully via proxy");
}

async function sendTextToAvatar(text, taskType = "talk") {
    // --- NEW WAITING LOGIC ---
    let waitTimeout = 40; // Wait for a maximum of 20 seconds (40 * 500ms)
    while (!isAvatarReady && waitTimeout > 0) {
        console.log("Avatar not ready, waiting...");
        await sleep(500); // sleep() is a helper function we already have
        waitTimeout--;
    }

    if (!isAvatarReady) {
        console.error("Avatar connection timed out. Could not send text.");
        // If the avatar fails, we still need to let the user's turn start.
        const speechDuration = estimateSpeechDuration(text);
        const buffer = 1500;
        await sleep(speechDuration + buffer);
        statusText.innerText = "Your turn to speak.";
        isUserTurn = true;
        return;
    }
    // --- END OF NEW LOGIC ---

    if (!heygenSessionInfo) {
        console.log("No active HeyGen session, skipping avatar.");
        return;
    }

    try {
        console.log(`LOG: Sending task '${taskType}' to proxy with text: "${text}"`);
        const response = await fetch('/api/heygen/task', {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                session_id: heygenSessionInfo.session_id,
                text: text,
                task_type: taskType,
            }),
        });

        if (!response.ok) {
            const errorData = await response.json();
            console.error(`Error sending task via proxy: ${errorData.message || response.statusText}`);
        }
    } catch (error) {
        console.error("Error sending text to avatar via proxy:", error);
    }
}

async function closeHeyGenSession() {
    if (!heygenSessionInfo) {
        return;
    }
    try {
        // Call our backend proxy
        await fetch(`/api/heygen/stop_session`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                token: heygenSessionToken,
                session_id: heygenSessionInfo.session_id,
            }),
        });
        if (heygenRoom) {
            await heygenRoom.disconnect();
        }
        avatarVideo.srcObject = null;
        avatarVideo.style.display = 'none';
        avatarPlaceholder.style.display = 'block';
        heygenSessionInfo = null;
        heygenRoom = null;
        heygenMediaStream = null;
        heygenSessionToken = null;
        updateAvatarStatus('disconnected', 'Avatar Closed');
        console.log("LOG: HeyGen session closed via proxy");
    } catch (error) {
        console.error("Error closing HeyGen session:", error);
    }
}

async function initializeHeyGenAvatar() {
    try {
        updateAvatarStatus('connecting', 'Initializing Avatar...');
        await createHeyGenSession();
        await startHeyGenStreamingSession();
        updateAvatarStatus('connected', 'Avatar Connected');
    } catch (error) {
        console.error("Error initializing HeyGen avatar:", error);
        updateAvatarStatus('disconnected', 'Avatar Failed');
        throw error;
    }
}


// --- 4. FASTAPI BACKEND COMMUNICATION ---
function connectToBackendControlSocket() {
    statusText.innerText = "Connecting to interview server...";
    const controlWsUrl = 'ws://' + window.location.host + '/ws/interview/' + sessionId + '/';
    controlSocket = new WebSocket(controlWsUrl);

    controlSocket.onopen = () => {
        console.log("LOG: Control Socket to FastAPI backend connected.");
        showAiLoadingBubble();
    };
    controlSocket.onmessage = async (event) => await onBackendMessage(event);
    controlSocket.onclose = () => {
        console.log("LOG: Control Socket to FastAPI backend closed.");
    };
    controlSocket.onerror = (err) => {
        console.error("Control Socket error:", err);
        statusText.innerText = "Connection error. Please refresh.";
    };
}

async function onBackendMessage(event) {
    const command = JSON.parse(event.data);
    console.log("LOG: Received command from backend:", command);

    removeLoadingBubble('ai-loading-bubble');

    if (command.type === 'new_question' && command.payload.text) {
        addMessageToChat(command.payload.text, 'ai');

        isUserTurn = false;
        statusText.innerText = "AI is speaking...";
        console.log("LOG: Mic gate closed (isUserTurn=false). Avatar is speaking.");

        await sendTextToAvatar(command.payload.text, "repeat"); // Changed to "talk"

        // This timer logic might need to be adjusted based on real avatar feedback
        // For now, we assume speaking is handled, and we just need a delay before user turn
        const speechDuration = estimateSpeechDuration(command.payload.text);
        const buffer = 1500;
        console.log(`LOG: Estimated speech time: ${speechDuration}ms. Mic will open in ${speechDuration + buffer}ms.`);

        await sleep(speechDuration + buffer);

        console.log("LOG: Timer finished. Opening mic gate (isUserTurn=true).");
        statusText.innerText = "Your turn to speak.";
        isUserTurn = true;
    }

    if (command.type === 'end_interview') {
        console.log("LOG: Received end_interview command.");
        endInterview();
    }
}

function submitTranscript(finalTranscript) {
    statusText.innerText = "AI is thinking...";
    showAiLoadingBubble();
    console.log("LOG: Submitting answer to backend:", finalTranscript);

    if (controlSocket && controlSocket.readyState === WebSocket.OPEN) {
        controlSocket.send(JSON.stringify({
            type: 'user_answer',
            payload: { answer: finalTranscript }
        }));
    } else {
        console.error("Cannot submit transcript, control socket is not open.");
        statusText.innerText = "Connection error. Please refresh.";
    }
    isUserTurn = false;
    console.log("LOG: Mic gate closed (isUserTurn=false). Waiting for next question.");
}


// --- 5. UI HELPER FUNCTIONS ---
function addMessageToChat(text, type) {
    const messageElement = document.createElement('div');
    messageElement.classList.add('message', `${type}-message`);
    messageElement.innerText = text;
    chatLog.appendChild(messageElement);
    chatLog.scrollTop = chatLog.scrollHeight;
    return messageElement;
}
function showUserLoadingBubble() {
    if (document.getElementById('user-loading-bubble')) return;
    const bubble = document.createElement('div');
    bubble.id = 'user-loading-bubble';
    bubble.classList.add('message', 'loading-bubble');
    bubble.innerHTML = `<span></span><span></span><span></span>`;
    chatLog.appendChild(bubble);
    chatLog.scrollTop = chatLog.scrollHeight;
}
function removeLoadingBubble(bubbleId) {
    const bubble = document.getElementById(bubbleId);
    if (bubble) bubble.remove();
}
function showAiLoadingBubble() {
    if (document.getElementById('ai-loading-bubble')) return;
    const bubble = document.createElement('div');
    bubble.id = 'ai-loading-bubble';
    bubble.classList.add('message', 'loading-bubble', 'ai');
    bubble.innerHTML = `<span></span><span></span><span></span>`;
    chatLog.appendChild(bubble);
    chatLog.scrollTop = chatLog.scrollHeight;
}


// --- 6. GLADIA TRANSCRIPTION LOGIC (PROXIED) ---
async function startGladiaConnection() {
    try {
        audioProcessor.stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: false });

        // This is the complete configuration object, as you requested
        const gladiaConfig = {
            encoding: "wav/pcm",
            sample_rate: 16000,
            model: "solaria-1",
            endpointing: 2,
            language_config: {
                languages: ["en", "id"],
                code_switching: false,
            },
            maximum_duration_without_endpointing: 60,
        };

        const initResponse = await fetch("/api/gladia/init", {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(gladiaConfig)
        });

        if (!initResponse.ok) throw new Error('Gladia API initialization via proxy failed.');
        const initData = await initResponse.json();

        gladiaSocket = new WebSocket(initData.url);
        gladiaSocket.onopen = () => processMicrophoneAudio();
        gladiaSocket.onmessage = onGladiaMessage;
        gladiaSocket.onclose = (event) => {
            console.log('LOG: Persistent Gladia socket closed.');
        };
        gladiaSocket.onerror = (err) => console.error('Gladia socket error:', err);

    } catch (err) {
        console.error("Gladia connection error:", err);
        statusText.innerText = `Error: ${err.message}`;
        throw err;
    }
}

// Replace the existing onGladiaMessage function with this one

// Replace the existing onGladiaMessage function with this one

function onGladiaMessage(event) {
    const data = JSON.parse(event.data);

    // --- ADD THIS LINE FOR DEBUGGING ---
    console.log("GLADIA MESSAGE RECEIVED:", data);
    // --- END OF DEBUGGING CODE ---

    if (data.type === 'speech_start' && isUserTurn) {
        showUserLoadingBubble();
    }

    if (data.type === 'transcript' && data.data && data.data.is_final) {
        if (isUserTurn) {
            // This line is still causing the error, which is expected for now.
            finalizeAndProceed(data.data.utterance.text);
        }
    }
}

function finalizeAndProceed(finalText) {
    isUserTurn = false;
    removeLoadingBubble('user-loading-bubble');

    if (finalText && finalText.trim().length > 0) {
        addMessageToChat(finalText, 'user');
        submitTranscript(finalText);
    }
}

function stopGladiaConnection() {
    console.log("LOG: Stopping Gladia connection...");
    if (gladiaSocket && gladiaSocket.readyState === WebSocket.OPEN) {
        gladiaSocket.send(JSON.stringify({ type: 'stop_recording' }));
        gladiaSocket.close();
    }
    if (audioProcessor.stream) {
        audioProcessor.stream.getTracks().forEach(track => track.stop());
        audioProcessor.stream = null;
    }
    if (audioProcessor.processor) audioProcessor.processor.disconnect();
    if (audioProcessor.context && audioProcessor.context.state !== 'closed') audioProcessor.context.close();
}

function processMicrophoneAudio() {
    const sampleRate = 16000;
    audioProcessor.context = new (window.AudioContext || window.webkitAudioContext)({ sampleRate });
    const source = audioProcessor.context.createMediaStreamSource(audioProcessor.stream);
    const bufferSize = 4096;
    audioProcessor.processor = audioProcessor.context.createScriptProcessor(bufferSize, 1, 1);

    audioProcessor.processor.onaudioprocess = (e) => {
        if (isUserTurn) {
            const inputData = e.inputBuffer.getChannelData(0);
            const pcmData = new Int16Array(inputData.length);
            for (let i = 0; i < inputData.length; i++) {
                pcmData[i] = inputData[i] * 0x7FFF;
            }
            const base64Data = btoa(String.fromCharCode.apply(null, new Uint8Array(pcmData.buffer)));

            if (gladiaSocket && gladiaSocket.readyState === WebSocket.OPEN) {
                gladiaSocket.send(JSON.stringify({ type: 'audio_chunk', data: { chunk: base64Data } }));
            }
        } else {
            const silentChunk = new Int16Array(bufferSize);
            const base64Data = btoa(String.fromCharCode.apply(null, new Uint8Array(silentChunk.buffer)));
            if (gladiaSocket && gladiaSocket.readyState === WebSocket.OPEN) {
                gladiaSocket.send(JSON.stringify({ type: 'audio_chunk', data: { chunk: base64Data } }));
            }
        }
    };
    source.connect(audioProcessor.processor);
    audioProcessor.processor.connect(audioProcessor.context.destination);
}


// --- 7. HELPER FUNCTIONS ---
function estimateSpeechDuration(text) {
    const wordsPerMinute = 150;
    const words = text.split(/\s+/).length;
    return (words / wordsPerMinute) * 60 * 1000;
}
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}
async function initializeUserCamera() {
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        userCamVideo.srcObject = stream;
    } catch (error) {
        console.error("Error accessing user camera:", error);
        const userCamContainer = document.getElementById('user-cam-container');
        userCamContainer.innerHTML = `<p style="color: white; text-align: center; padding: 10px;">Could not access camera.</p>`;
    }
}
function startInterviewTimer(minutes) {
    let duration = minutes * 60;
    interviewTimer = setInterval(() => {
        const mins = Math.floor(duration / 60);
        const secs = duration % 60;
        const displayMins = String(mins).padStart(2, '0');
        const displaySecs = String(secs).padStart(2, '0');
        timerDisplay.innerText = `${displayMins}:${displaySecs}`;

        if (--duration < 0) {
            clearInterval(interviewTimer);
            timerDisplay.innerText = "00:00";
            addMessageToChat("Time is up. The interview will now conclude.", "ai");
            endInterview();
        }
    }, 1000);
}


// --- 8. INITIALIZATION ---
document.addEventListener('DOMContentLoaded', init);
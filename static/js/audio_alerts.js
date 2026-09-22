// Web Audio API emergency alert sound generator
class EmergencyAudioAlert {
    constructor() {
        this.audioCtx = null;
        this.alarmInterval = null;
        this.isPlaying = false;
    }

    init() {
        if (!this.audioCtx) {
            const AudioContext = window.AudioContext || window.webkitAudioContext;
            this.audioCtx = new AudioContext();
        }
        if (this.audioCtx.state === 'suspended') {
            this.audioCtx.resume();
        }
    }

    playBeep(freq = 880, duration = 0.18, type = 'sine') {
        try {
            this.init();
            const osc = this.audioCtx.createOscillator();
            const gain = this.audioCtx.createGain();

            osc.type = type;
            osc.frequency.setValueAtTime(freq, this.audioCtx.currentTime);

            gain.gain.setValueAtTime(0.3, this.audioCtx.currentTime);
            gain.gain.exponentialRampToValueAtTime(0.001, this.audioCtx.currentTime + duration);

            osc.connect(gain);
            gain.connect(this.audioCtx.destination);

            osc.start();
            osc.stop(this.audioCtx.currentTime + duration);
        } catch (e) {
            console.warn("Audio context not allowed yet without user gesture", e);
        }
    }

    startFallAlarm() {
        if (this.isPlaying) return;
        this.isPlaying = true;
        this.init();

        const playChimeSequence = () => {
            this.playBeep(920, 0.15, 'sawtooth');
            setTimeout(() => this.playBeep(1200, 0.22, 'triangle'), 160);
        };

        playChimeSequence();
        this.alarmInterval = setInterval(playChimeSequence, 1200);
    }

    stopFallAlarm() {
        this.isPlaying = false;
        if (this.alarmInterval) {
            clearInterval(this.alarmInterval);
            this.alarmInterval = null;
        }
    }
}

window.emergencyAudio = new EmergencyAudioAlert();

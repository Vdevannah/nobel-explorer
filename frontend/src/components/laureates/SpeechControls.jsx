import { useEffect, useRef, useState } from "react";

const SENTENCE_PAUSE_MS = 180;
const PARAGRAPH_PAUSE_MS = 520;

function splitIntoChunks(text) {
  const segmenter = typeof Intl.Segmenter === "function"
    ? new Intl.Segmenter("en", { granularity: "sentence" })
    : null;

  return text
    .split(/\n\s*\n/)
    .flatMap((paragraph, paragraphIndex) => {
      const sentences = segmenter
        ? Array.from(segmenter.segment(paragraph), ({ segment }) => segment.trim())
        : (paragraph.match(/[^.!?]+(?:[.!?]+["')\]]*|$)/g) || [paragraph])
          .map((sentence) => sentence.trim());
      return sentences
        .filter(Boolean)
        .map((sentence) => ({ text: sentence, paragraphIndex }));
    });
}

function getEnglishVoice(synthesis) {
  let voices = [];
  try {
    voices = synthesis.getVoices();
  } catch {
    return null;
  }

  const englishVoices = voices.filter((voice) => /^en(?:[-_]|$)/i.test(voice.lang));
  const qualityHints = /natural|premium|enhanced|neural|siri|google|microsoft|ava|aria|jenny|samantha|daniel/i;
  const scoreVoice = (voice) =>
    (qualityHints.test(voice.name) ? 5 : 0) +
    (/^en[-_]?(us|gb|au|ca)/i.test(voice.lang) ? 2 : 0) +
    (voice.default ? 1 : 0);

  return englishVoices.sort((left, right) => scoreVoice(right) - scoreVoice(left))[0]
    ?? voices.find((voice) => voice.default)
    ?? null;
}

function SpeechControls({ text, resetKey, audioSrc }) {
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [status, setStatus] = useState("");
  const utteranceRef = useRef(null);
  const audioRef = useRef(null);
  const timerRef = useRef(null);
  const runIdRef = useRef(0);

  function cancelPlayback() {
    runIdRef.current += 1;
    if (typeof window !== "undefined") {
      window.speechSynthesis?.cancel();
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      }
    }
    audioRef.current = null;
    utteranceRef.current = null;
    window.clearTimeout(timerRef.current);
    timerRef.current = null;
  }

  useEffect(() => {
    setIsSpeaking(false);
    setStatus("");

    return () => {
      cancelPlayback();
    };
  }, [resetKey, text, audioSrc]);

  function stopPlayback() {
    cancelPlayback();
    setIsSpeaking(false);
    setStatus("Narration stopped");
  }

  function speakWithBrowser(runId) {
    if (
      typeof window === "undefined" ||
      !window.speechSynthesis ||
      !window.SpeechSynthesisUtterance
    ) {
      if (runId === runIdRef.current) setIsSpeaking(false);
      setStatus("Speech is unavailable in this browser");
      return;
    }

    window.speechSynthesis.cancel();
    const chunks = splitIntoChunks(text);
    const voice = getEnglishVoice(window.speechSynthesis);
    let chunkIndex = 0;

    function speakNext() {
      if (runIdRef.current !== runId) return;
      if (chunkIndex >= chunks.length) {
        utteranceRef.current = null;
        setIsSpeaking(false);
        setStatus("Narration finished");
        return;
      }

      const chunk = chunks[chunkIndex];
      const utterance = new window.SpeechSynthesisUtterance(chunk.text);
      utterance.rate = 0.9;
      utterance.pitch = 1.0;
      if (voice) {
        utterance.voice = voice;
        utterance.lang = voice.lang;
      }
      utterance.onend = () => {
        if (runIdRef.current !== runId) return;
        utteranceRef.current = null;
        chunkIndex += 1;
        if (chunkIndex < chunks.length) {
          const isNextParagraph = chunks[chunkIndex].paragraphIndex !== chunk.paragraphIndex;
          timerRef.current = window.setTimeout(
            speakNext,
            isNextParagraph ? PARAGRAPH_PAUSE_MS : SENTENCE_PAUSE_MS,
          );
        } else {
          speakNext();
        }
      };
      utterance.onerror = () => {
        if (runIdRef.current === runId) {
          cancelPlayback();
          setIsSpeaking(false);
          setStatus("Narration could not be played");
        }
      };

      utteranceRef.current = utterance;
      window.speechSynthesis.speak(utterance);
    }

    speakNext();
  }

  function startPrerecordedAudio(src, runId) {
    let audio;
    try {
      audio = new window.Audio(src);
    } catch {
      speakWithBrowser(runId);
      return;
    }

    audioRef.current = audio;
    audio.onended = () => {
      if (runIdRef.current !== runId || audioRef.current !== audio) return;
      audioRef.current = null;
      setIsSpeaking(false);
      setStatus("Narration finished");
    };
    const fallbackToBrowserSpeech = () => {
      if (runIdRef.current !== runId || audioRef.current !== audio) return;
      audioRef.current = null;
      audio.pause();
      audio.currentTime = 0;
      speakWithBrowser(runId);
    };
    audio.onerror = fallbackToBrowserSpeech;
    audio.play().catch(fallbackToBrowserSpeech);
  }

  function startPlayback() {
    if (typeof window === "undefined") {
      setStatus("Audio is unavailable in this browser");
      return;
    }

    const runId = cancelPlayback();
    setIsSpeaking(true);
    setStatus("Narration playing");
    if (audioSrc && typeof window.Audio === "function") {
      startPrerecordedAudio(audioSrc, runId);
    } else {
      speakWithBrowser(runId);
    }
  }

  return (
    <div className="learning-speech-controls">
      <button
        className="learning-speech-button"
        type="button"
        aria-label={isSpeaking ? "Stop narration" : "Listen to explanation"}
        disabled={!text.trim()}
        onClick={isSpeaking ? stopPlayback : startPlayback}
      >
        {isSpeaking ? (
          <>
            <svg viewBox="0 0 24 24" aria-hidden="true" focusable="false">
              <rect x="6" y="6" width="12" height="12" fill="currentColor" />
            </svg>
            Stop
          </>
        ) : (
          <>
            <svg className="learning-speech-speaker-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
              <path d="M3 9v6h4l5 4V5L7 9H3Z" fill="currentColor" />
              <path d="M16 9a5 5 0 0 1 0 6m3-9a9 9 0 0 1 0 12" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
            Listen
          </>
        )}
      </button>
      <span className="visually-hidden" role="status" aria-live="polite" aria-atomic="true">
        {status}
      </span>
    </div>
  );
}

export default SpeechControls;
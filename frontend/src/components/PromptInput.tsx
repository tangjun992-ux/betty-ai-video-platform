"use client";

import { useState, useRef, useEffect } from "react";

interface PromptInputProps {
  value: string;
  onChange: (val: string) => void;
  placeholder?: string;
}

export function PromptInput({ value, onChange, placeholder }: PromptInputProps) {
  const [rows, setRows] = useState(4);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleInput = () => {
    const textarea = textareaRef.current;
    if (textarea) {
      const lineCount = textarea.value.split("\n").length;
      setRows(Math.max(4, Math.min(lineCount, 12)));
      // Auto-adjust height
      textarea.style.height = "auto";
      textarea.style.height = `${Math.max(144, textarea.scrollHeight)}px`;
    }
  };

  useEffect(() => {
    handleInput();
  }, [value]);

  return (
    <div className="relative">
      <textarea
        ref={textareaRef}
        value={value}
        onChange={(e) => {
          onChange(e.target.value);
          handleInput();
        }}
        placeholder={placeholder}
        rows={rows}
        className="w-full bg-dark-900/60 border border-dark-800 rounded-xl p-4 text-text-accent-cyan placeholder-dark-500 focus:outline-none focus:border-accent-cyan focus:ring-1 focus:ring-accent-cyan/30 resize-y transition text-base leading-relaxed"
        maxLength={2000}
      />
      <div className="absolute bottom-2 right-4 text-xs text-dark-500">{value.length}/2000</div>
    </div>
  );
}

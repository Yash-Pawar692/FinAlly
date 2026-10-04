"use client";

import { useEffect, useRef, useState } from "react";

export type FlashDirection = "up" | "down" | null;

/**
 * Tracks a numeric value and returns a (direction, key) pair that changes
 * whenever the value moves. Consumers key the flashing element by `key` so
 * React remounts it on every change — required for the CSS flash animation
 * to replay even when two consecutive changes are in the same direction
 * (reapplying an unchanged class name would not restart the animation).
 */
export function useFlash(value: number | null | undefined) {
  const [direction, setDirection] = useState<FlashDirection>(null);
  const [flashKey, setFlashKey] = useState(0);
  const prevRef = useRef(value);

  useEffect(() => {
    const prev = prevRef.current;
    if (value != null && prev != null && value !== prev) {
      setDirection(value > prev ? "up" : "down");
      setFlashKey((key) => key + 1);
    }
    prevRef.current = value;
  }, [value]);

  return { direction, flashKey };
}

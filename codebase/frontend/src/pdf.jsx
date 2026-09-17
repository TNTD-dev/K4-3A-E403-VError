import React, { useEffect, useRef, useState } from "react";
import * as pdfjs from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

const documents = new Map();

function loadDocument(url) {
  if (!documents.has(url)) {
    const task = pdfjs.getDocument({ url }).promise.catch(error => {
      documents.delete(url);
      throw error;
    });
    documents.set(url, task);
  }
  return documents.get(url);
}

export function usePdf(url) {
  const [state, setState] = useState({ doc: null, error: "", ratio: 16 / 9 });
  useEffect(() => {
    if (!url) return undefined;
    let live = true;
    loadDocument(url)
      .then(async doc => {
        const first = await doc.getPage(1);
        const { width, height } = first.getViewport({ scale: 1 });
        if (live) setState({ doc, error: "", ratio: width / height });
      })
      .catch(error => live && setState({ doc: null, error: error.message || "Không mở được PDF", ratio: 16 / 9 }));
    return () => {
      live = false;
    };
  }, [url]);
  return state;
}

/** Returns [callbackRef, width]; works even when the measured element mounts later. */
export function useElementWidth(step = 20) {
  const [node, setNode] = useState(null);
  const [width, setWidth] = useState(0);
  useEffect(() => {
    if (!node) return undefined;
    const observer = new ResizeObserver(([entry]) => {
      // Snap to a step so small layout jitters do not re-render the canvas.
      setWidth(Math.round(entry.contentRect.width / step) * step);
    });
    observer.observe(node);
    return () => observer.disconnect();
  }, [node, step]);
  return [setNode, width];
}

function useInView(ref, enabled) {
  const [seen, setSeen] = useState(!enabled);
  useEffect(() => {
    if (!enabled || seen || !ref.current) return undefined;
    const observer = new IntersectionObserver(
      entries => entries.some(entry => entry.isIntersecting) && setSeen(true),
      { rootMargin: "600px 0px" },
    );
    observer.observe(ref.current);
    return () => observer.disconnect();
  }, [ref, enabled, seen]);
  return seen;
}

/** Renders one PDF page. Draws off-screen first so page changes never flash blank. */
export function PdfCanvas({ doc, page, width, className = "", lazy = false }) {
  const ref = useRef(null);
  const visible = useInView(ref, lazy);
  useEffect(() => {
    if (!doc || !width || !visible || !ref.current) return undefined;
    let cancelled = false;
    let task = null;
    (async () => {
      try {
        const pdfPage = await doc.getPage(page);
        if (cancelled) return;
        const base = pdfPage.getViewport({ scale: 1 });
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        const viewport = pdfPage.getViewport({ scale: (width / base.width) * dpr });
        const buffer = document.createElement("canvas");
        buffer.width = Math.floor(viewport.width);
        buffer.height = Math.floor(viewport.height);
        task = pdfPage.render({ canvas: buffer, viewport });
        await task.promise;
        if (cancelled || !ref.current) return;
        const target = ref.current;
        target.width = buffer.width;
        target.height = buffer.height;
        target.getContext("2d").drawImage(buffer, 0, 0);
      } catch (error) {
        if (error?.name !== "RenderingCancelledException") console.warn("PDF render failed", error);
      }
    })();
    return () => {
      cancelled = true;
      task?.cancel();
    };
  }, [doc, page, width, visible]);
  return <canvas ref={ref} className={className} />;
}

/** Small JPEG previews for the thumbnail strip, rendered one by one in the background. */
export function useThumbnails(doc, width = 176) {
  const [thumbs, setThumbs] = useState({});
  useEffect(() => {
    if (!doc) return undefined;
    let cancelled = false;
    (async () => {
      for (let number = 1; number <= doc.numPages; number += 1) {
        if (cancelled) return;
        try {
          const pdfPage = await doc.getPage(number);
          const base = pdfPage.getViewport({ scale: 1 });
          const viewport = pdfPage.getViewport({ scale: (width * 1.5) / base.width });
          const canvas = document.createElement("canvas");
          canvas.width = Math.floor(viewport.width);
          canvas.height = Math.floor(viewport.height);
          await pdfPage.render({ canvas, viewport }).promise;
          const url = canvas.toDataURL("image/jpeg", 0.78);
          if (!cancelled) setThumbs(current => ({ ...current, [number]: url }));
        } catch (error) {
          console.warn("Thumbnail render failed", number, error);
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [doc, width]);
  return thumbs;
}

const veils = new Map();

/** A 48px, pre-softened copy of a thumbnail. Upscaled it reads as a blur without any CSS filter cost. */
export function useVeil(src) {
  const [veil, setVeil] = useState(() => (src && veils.get(src)) || null);
  useEffect(() => {
    if (!src) return undefined;
    if (veils.has(src)) {
      setVeil(veils.get(src));
      return undefined;
    }
    let live = true;
    const image = new Image();
    image.onload = () => {
      const canvas = document.createElement("canvas");
      canvas.width = 48;
      canvas.height = Math.max(1, Math.round((48 * image.height) / image.width));
      const context = canvas.getContext("2d");
      context.filter = "blur(1.2px)";
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      const url = canvas.toDataURL("image/png");
      veils.set(src, url);
      if (live) setVeil(url);
    };
    image.src = src;
    return () => {
      live = false;
    };
  }, [src]);
  return veil;
}

/**
 * The slide itself. While a page is gated the real page is never rendered at full
 * resolution: learners only see a blurred preview until they answer the pre-quiz.
 */
export function SlideSurface({ doc, page, width, gated, preview, lazy = false }) {
  const veil = useVeil(preview);
  return (
    <>
      {veil && <img className={`slide-veil ${gated ? "gated" : ""}`} src={veil} alt="" aria-hidden="true" />}
      {!gated && doc && <PdfCanvas doc={doc} page={page} width={width} className="slide-canvas" lazy={lazy} />}
    </>
  );
}

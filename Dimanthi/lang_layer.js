/*
  Translation layer for the guide cards (OSHC Compass) - Dimi's part

  language_box.inject() puts this script at the end of a guide's HTML.
  It translates every piece of text the guide shows into the student's language,
  WITHOUT changing the guide's own code:

    - finds every text on the page (and new text the guide shows later, e.g. the next step)
    - looks it up in the translations (same rules as language_box.translate in Python):
        1. the whole text            2. templates like "Step 3 of 7: ..."
        3. sentence by sentence      4. unknown -> stays English (never a wrong guess)
    - Farsi: the page reads right to left, numbers / $ / English names stay left to right
    - keeps in English what must stay English: the "What to say" English sentence,
      the language buttons, glossary terms, website address bars, data-keep elements
*/
(function () {
  "use strict";

  const DATA = __LANG_DATA__;
  const LRI = "⁦", PDI = "⁩";
  const NO_SPLIT_AFTER = ["e.g.", "eg.", "i.e.", "etc.", "p.", "No."];
  const KEEP = "#ft1,#ft2,.urlbar,.term,#sayEn,.say-en,#sayTr,.say-tr,.lang,#langButtons,[data-lang]," +
               "script,style,noscript,[data-keep]";
  const SVG_OK = ".sign-text,#bubbleText,#bubbleLabel";

  // ---------- Translating one text (same as Python) ----------

  const templates = Object.entries(DATA.templates).map(([en, out]) => {
    const esc = en.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")
      .replace("\\{n\\}", "(?<n>\\d+)").replace("\\{t\\}", "(?<t>\\d+)").replace("\\{x\\}", "(?<x>[\\s\\S]+)");
    return [new RegExp("^" + esc + "$"), out];
  });

  function splitSentences(text) {
    const parts = [];
    const re = /[.!?]\s+(?=[A-Z“‘(])/g;
    let start = 0, m;
    while ((m = re.exec(text)) !== null) {
      const piece = text.slice(start, m.index + m[0].length).trim();
      if (NO_SPLIT_AFTER.includes(piece.split(/\s+/).pop().replace(/^[(“‘]+/, ""))) continue;   // a short form, not the end
      parts.push(piece);
      start = m.index + m[0].length;
    }
    if (text.slice(start).trim()) parts.push(text.slice(start).trim());
    return parts;
  }

  function isolate(text) {
    return text.replace(/([$+]?[0-9A-Za-z][0-9A-Za-z'’&./:%,\- ]*[0-9A-Za-z.%]|[$+]?[0-9A-Za-z]%?)/g,
      s => LRI + (/^[$+]?\d[\d ]*\d$/.test(s) ? s.replace(/ /g, "\u00a0") : s) + PDI);   // phone numbers stay on one line
  }

  function one(piece) {
    if (DATA.sentences[piece]) return DATA.sentences[piece];
    for (const [re, out] of templates) {
      const m = piece.match(re);
      if (m) {
        const v = Object.assign({}, m.groups);
        if (v.x !== undefined) v.x = translate(v.x, true);
        return out.replace(/\{(n|t|x)\}/g, (_, k) => v[k]);
      }
    }
    return null;
  }

  function translate(text, inner) {
    if (!text || !/[A-Za-z]/.test(text)) return text;
    const m = text.match(/^(\s*)([\s\S]*?)(\s*)$/);
    const core = m[2].replace(/\s+/g, " ");   // HTML line breaks and double spaces -> one space
    let whole = one(core);
    if (whole === null) {
      // Sentence by sentence. Two or more sentences that were translated together are used together.
      const sentences = splitSentences(core), pieces = [];
      let i = 0;
      while (i < sentences.length) {
        let j = sentences.length, done = null;
        for (; j > i; j--) { done = one(sentences.slice(i, j).join(" ")); if (done !== null) break; }
        if (done === null) { done = sentences[i]; j = i + 1; }
        pieces.push(done);
        i = j;
      }
      whole = pieces.join(" ");
    }
    if (DATA.rtl && !inner) whole = isolate(whole);
    return m[1] + whole + m[3];
  }

  // ---------- Walking the page ----------

  const original = new WeakMap();   // text node -> the English the guide wrote
  const shown = new WeakMap();      // text node -> what we put there
  let busy = false;

  function skip(node) {
    const el = node.parentElement;
    if (!el) return true;
    if (el.closest(KEEP)) return true;
    if (el.closest("svg") && !el.closest(SVG_OK)) return true;
    return false;
  }

  function doNode(node) {
    if (skip(node)) return;
    const now = node.nodeValue;
    // The guide changed this text since we translated it -> it is new English
    if (!original.has(node) || shown.get(node) !== now) original.set(node, now);
    const out = translate(original.get(node));
    shown.set(node, out);
    if (out !== now) node.nodeValue = out;
  }

  function doAttributes(root) {
    root.querySelectorAll("[placeholder],[title],[aria-label]").forEach(el => {
      if (el.closest(KEEP)) return;
      ["placeholder", "title", "aria-label"].forEach(a => {
        const v = el.getAttribute(a);
        if (!v) return;
        const key = "data-en-" + a;
        if (!el.hasAttribute(key) || el.getAttribute("data-tr-" + a) !== v) el.setAttribute(key, v);
        const out = translate(el.getAttribute(key));
        el.setAttribute("data-tr-" + a, out);
        if (out !== v) el.setAttribute(a, out);
      });
    });
  }

  // SVG text does not wrap: make the speech bubble and the station signs fit the new words
  function fitSvg() {
    const text = document.getElementById("bubbleText");
    const box = document.getElementById("bubbleBox");
    if (text && box && text.textContent) {
      try {
        const label = document.getElementById("bubbleLabel");
        const need = Math.max(text.getComputedTextLength(), label ? label.getComputedTextLength() : 0);
        const oldLeft = parseFloat(box.getAttribute("x")) || 0;
        const oldWidth = parseFloat(box.getAttribute("width")) || 200;
        const centre = oldLeft + oldWidth / 2;
        const width = Math.max(200, need + 28);
        const left = Math.min(1110 - width, Math.max(10, centre - width / 2));
        box.setAttribute("width", width);
        box.setAttribute("x", left);
        text.setAttribute("x", left + 14);
        if (label) label.setAttribute("x", left + 14);
      } catch (e) { /* hidden: nothing to measure */ }
    }
    document.querySelectorAll(".sign-text").forEach(t => {
      try {
        t.removeAttribute("textLength");
        if (t.getComputedTextLength() > 94) {
          t.setAttribute("textLength", 94);
          t.setAttribute("lengthAdjust", "spacingAndGlyphs");
        }
      } catch (e) { /* ignore */ }
    });
  }

  function run() {
    if (busy) return;
    busy = true;
    try {
      const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
      const nodes = [];
      while (walker.nextNode()) nodes.push(walker.currentNode);
      nodes.forEach(doNode);
      doAttributes(document.body);
      fitSvg();
    } finally {
      observer.takeRecords();   // ignore the changes we just made
      busy = false;
    }
    resizeFrame();
  }

  function resizeFrame() {
    try {
      const h = document.documentElement.scrollHeight;
      window.parent.postMessage({ isStreamlitMessage: true, type: "streamlit:setFrameHeight", height: h }, "*");
    } catch (e) { /* not inside Streamlit */ }
  }

  let timer = null;
  const observer = new MutationObserver(() => {
    if (busy) return;
    clearTimeout(timer);
    timer = setTimeout(run, 30);
  });

  // ---------- Start ----------

  document.documentElement.lang = DATA.lang;
  if (DATA.rtl) {
    document.body.dir = "rtl";
    const style = document.createElement("style");
    // Pictures, animations and website screenshots keep their left-to-right layout
    style.textContent = "svg,.scene,.stage,.hall,#scroll,.urlbar,.shot,.phone,.lang,#langButtons{direction:ltr}" +
                        "#sayEn,.say-en{direction:ltr;text-align:left}" +
                        // Farsi letters join together: letter spacing would break the words apart
                        "*{letter-spacing:normal!important}";
    document.head.appendChild(style);
  }
  run();

  // The meaning model found where the student needs to be: walk there
  if (DATA.goto !== null && DATA.goto !== undefined) {
    setTimeout(() => {
      try {
        if (typeof goToStep === "function") {            // hospital: walk along the hallway
          if (typeof stopPlaying === "function") stopPlaying();
          goToStep(DATA.goto);
        } else if (typeof go === "function") {           // homesick: spin the wheel once round, then stop at the answer
          if (typeof stopPlaying === "function") stopPlaying();
          const slow = "transform 2.4s cubic-bezier(.2,.7,.15,1)";
          const parts = [document.getElementById("wheel"), ...document.querySelectorAll(".up")];
          parts.forEach(el => { if (el) el.style.transition = slow; });
          const turns = typeof N === "number" ? N : 6;
          go(turns + DATA.goto);                          // one full turn + the right suggestion
          setTimeout(() => parts.forEach(el => { if (el) el.style.transition = ""; }), 2600);
        }
      } catch (e) { /* the guide changed: stay where it is */ }
    }, 400);
  }
  observer.observe(document.body, { childList: true, subtree: true, characterData: true,
                                    attributes: true, attributeFilter: ["placeholder", "title", "aria-label"] });
})();

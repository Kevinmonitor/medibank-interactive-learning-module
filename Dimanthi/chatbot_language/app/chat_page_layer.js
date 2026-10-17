/* Page translation layer for the OSHC chatbot - Dimi's part
   Translates the page text (headings, the five tips, the sidebar, the "What this is based on"
   panel, the processing steps) into the chosen language, without changing Muhammad's page code.
   It keeps watching the page, so text that appears later (new answers) is translated too.
   Choosing English puts every original sentence back. */
(function () {
  const P = window.parent, doc = P.document;
  const DATA = __DATA__;            // {lang, rtl, page: {english: translation}, patterns: [[regex, template]]}
  const store = P.__oshcLang || (P.__oshcLang = { orig: new P.WeakMap(), observer: null });
  if (store.observer) store.observer.disconnect();

  const SKIP = new Set(["SCRIPT", "STYLE", "TEXTAREA", "INPUT", "CODE", "PRE"]);
  const patterns = DATA.patterns.map(([re, t]) => [new RegExp(re), t]);

  function translate(text) {
    const trimmed = text.trim();
    if (!trimmed) return null;
    // keep an emoji or icon in front ("✅ Safety check")
    const m = trimmed.match(/^([^\p{L}\p{N}]*)(.*)$/u);
    const prefix = m[1], body = m[2];
    if (DATA.page[body]) return text.replace(trimmed, prefix + DATA.page[body]);
    for (const [re, t] of patterns) if (re.test(body)) return text.replace(trimmed, prefix + body.replace(re, t));
    return null;
  }

  function fix(node) {
    if (node.nodeType !== 3 || !node.parentElement || SKIP.has(node.parentElement.tagName)) return;
    if (node.parentElement.closest("[data-testid='stChatMessage'] .stAlert")) return;   // answers are done in Python
    const known = store.orig.get(node);
    const original = known && node.nodeValue === known.shown ? known.text : node.nodeValue;
    if (DATA.lang === "en") {
      if (known && node.nodeValue === known.shown) node.nodeValue = known.text;
      store.orig.delete(node);
      return;
    }
    const out = translate(original);
    if (out && out !== node.nodeValue) {
      node.nodeValue = out;
      store.orig.set(node, { text: original, shown: out });
    }
  }

  function walk(root) {
    const w = doc.createTreeWalker(root, 4);
    let n;
    while ((n = w.nextNode())) fix(n);
  }

  walk(doc.body);
  if (DATA.lang === "en") return;
  store.observer = new P.MutationObserver(list => {
    for (const r of list) {
      if (r.type === "characterData") fix(r.target);
      for (const n of r.addedNodes) n.nodeType === 3 ? fix(n) : n.nodeType === 1 && walk(n);
    }
  });
  store.observer.observe(doc.body, { childList: true, subtree: true, characterData: true });
})();

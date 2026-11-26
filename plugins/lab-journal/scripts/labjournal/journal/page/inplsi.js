// features that run in PLSI: one card with the link
const inPlsi = (text) => {
  const box = h("div"), a = h("a", null, "longevitygrok.si");
  a.href = "https://longevitygrok.si/"; a.target = "_blank"; a.rel = "noopener";
  box.appendChild(h("p", null, text.split(" https://longevitygrok.si/")[0].replace(/:$/, "."))); box.appendChild(a);
  return box;
};

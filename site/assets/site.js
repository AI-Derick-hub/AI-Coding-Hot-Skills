(function () {
  const grid = document.querySelector("#grid");
  const cards = Array.from(document.querySelectorAll(".card"));
  const search = document.querySelector("#q");
  const rule = document.querySelector("#rule");
  const sort = document.querySelector("#sort");
  const count = document.querySelector("#result-count");
  const empty = document.querySelector("#empty");
  const chips = Array.from(document.querySelectorAll(".chip"));
  const state = { q: "", cat: "", rule: "all", sort: "stars" };

  function readUrl() {
    const params = new URLSearchParams(location.search);
    state.q = params.get("q") || "";
    state.cat = params.get("cat") || "";
    state.rule = params.get("rule") || "all";
    state.sort = params.get("sort") || "stars";
    search.value = state.q;
    rule.value = state.rule;
    sort.value = state.sort;
    chips.forEach((chip) => {
      chip.setAttribute("aria-pressed", String((chip.dataset.cat || "") === state.cat));
    });
  }

  function writeUrl() {
    const params = new URLSearchParams();
    if (state.q) params.set("q", state.q);
    if (state.cat) params.set("cat", state.cat);
    if (state.rule !== "all") params.set("rule", state.rule);
    if (state.sort !== "stars") params.set("sort", state.sort);
    const next = params.toString();
    history.replaceState(null, "", next ? `?${next}` : location.pathname);
  }

  function apply() {
    const query = state.q.trim().toLowerCase();
    const visible = cards.filter((card) => {
      const cats = (card.dataset.cats || "").split(",").filter(Boolean);
      const catOk = !state.cat || cats.includes(state.cat);
      const ruleOk =
        state.rule === "all" ||
        card.dataset.rule === state.rule ||
        (state.rule === "new" && card.dataset.new === "1");
      const textOk = !query || (card.dataset.search || "").includes(query);
      const show = catOk && ruleOk && textOk;
      card.hidden = !show;
      return show;
    });
    const sorters = {
      stars: (a, b) => Number(b.dataset.stars) - Number(a.dataset.stars),
      updated: (a, b) => (b.dataset.pushed || "").localeCompare(a.dataset.pushed || ""),
      name: (a, b) => (a.dataset.name || "").localeCompare(b.dataset.name || "", "zh"),
      new: (a, b) => Number(b.dataset.new) - Number(a.dataset.new) || Number(b.dataset.stars) - Number(a.dataset.stars),
    };
    visible.sort(sorters[state.sort] || sorters.stars);
    visible.forEach((card) => grid.appendChild(card));
    count.textContent = `${visible.length} 个结果`;
    empty.hidden = visible.length !== 0;
  }

  chips.forEach((chip) => {
    chip.addEventListener("click", () => {
      state.cat = chip.dataset.cat || "";
      chips.forEach((item) => item.setAttribute("aria-pressed", String(item === chip)));
      writeUrl();
      apply();
    });
  });
  search.addEventListener("input", () => {
    state.q = search.value;
    writeUrl();
    apply();
  });
  rule.addEventListener("change", () => {
    state.rule = rule.value;
    writeUrl();
    apply();
  });
  sort.addEventListener("change", () => {
    state.sort = sort.value;
    writeUrl();
    apply();
  });

  readUrl();
  apply();
})();

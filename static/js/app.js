(function () {
    const field = document.getElementById("glyph-field");
    if (!field) return;

    const total = 9 * 11;
    const glyphs = [];
    for (let i = 0; i < total; i++) {
        const g = document.createElement("span");
        g.className = "glyph";
        g.textContent = "\u2014";
        field.appendChild(g);
        glyphs.push(g);
    }

    function aimAt(x, y) {
        glyphs.forEach(function (g) {
            const r = g.getBoundingClientRect();
            const angle = Math.atan2(y - (r.top + r.height / 2), x - (r.left + r.width / 2));
            g.style.transform = "rotate(" + angle + "rad)";
        });
    }

    const box = field.getBoundingClientRect();
    aimAt(box.left + box.width / 2, box.top - 120);

    let waiting = false;
    document.addEventListener("mousemove", function (e) {
        if (waiting) return;
        waiting = true;
        requestAnimationFrame(function () {
            aimAt(e.clientX, e.clientY);
            waiting = false;
        });
    });
})();
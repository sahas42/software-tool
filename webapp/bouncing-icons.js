/**
 * bouncing-icons.js  (v2 — 5-zone spread)
 *
 * Each .float-icon is placed in its OWN zone of the viewport so they all
 * start as far apart from each other as possible.
 *
 *  Zone layout (5 icons):
 *
 *    ┌────────┬────────┐
 *    │  [0]   │  [1]   │
 *    ├────────┼────────┤
 *    │  [2]   │  [3]   │
 *    ├────────┴────────┤
 *    │      [4]        │
 *    └─────────────────┘
 *
 * Every icon gets a UNIQUE random direction (angle) that is spread ≥72° apart
 * from its neighbours so they never travel in similar directions at the start.
 */
(function () {

    // Zone definitions as fractions [xMin, xMax, yMin, yMax]
    const ZONES = [
        [0.00, 0.45, 0.00, 0.48],   // top-left
        [0.55, 1.00, 0.00, 0.48],   // top-right
        [0.00, 0.45, 0.52, 1.00],   // bottom-left
        [0.55, 1.00, 0.52, 1.00],   // bottom-right
        [0.25, 0.75, 0.38, 0.62],   // centre (behind the form glass, still visible)
    ];

    // Base speeds per icon — all slightly different so they drift apart over time
    const BASE_SPEEDS = [1.1, 1.4, 0.9, 1.3, 1.0];

    function init() {
        const icons = Array.from(document.querySelectorAll('.float-icon'));
        if (!icons.length) return;

        const W = window.innerWidth;
        const H = window.innerHeight;

        // Pre-generate angles that are ≥ 72° apart (360/5 = 72)
        // Start from a random offset so it's different every load
        const baseAngle = Math.random() * Math.PI * 2;
        const angles = icons.map((_, i) =>
            baseAngle + i * ((Math.PI * 2) / icons.length) + (Math.random() - 0.5) * 0.6
        );

        const balls = icons.map((el, i) => {
            const size = el.offsetWidth || 70;
            const zone = ZONES[i % ZONES.length];

            // Random position WITHIN the assigned zone
            const zW = (zone[1] - zone[0]) * W - size;
            const zH = (zone[3] - zone[2]) * H - size;
            const x = zone[0] * W + Math.random() * Math.max(zW, 0);
            const y = zone[2] * H + Math.random() * Math.max(zH, 0);

            // Apply unique random angle from the spread-out set
            const angle = angles[i];
            const speed = BASE_SPEEDS[i % BASE_SPEEDS.length];

            // Position via transform; no CSS top/left so they don't jump
            el.style.position = 'fixed';
            el.style.top = '0px';
            el.style.left = '0px';
            el.style.margin = '0';
            el.style.willChange = 'transform';
            el.style.transform = `translate(${x}px, ${y}px)`;

            return {
                el, size,
                x, y,
                vx: Math.cos(angle) * speed,
                vy: Math.sin(angle) * speed,
                scaleX: 1, scaleY: 1,
                squishing: false,
                squishTimer: null,
            };
        });

        // ── Elastic squish ────────────────────────────────────────────
        function squish(ball, sx, sy) {
            if (ball.squishing) return;
            ball.squishing = true;
            ball.scaleX = sx;
            ball.scaleY = sy;
            if (ball.squishTimer) clearTimeout(ball.squishTimer);
            ball.squishTimer = setTimeout(() => {
                ball.scaleX = 1.1; ball.scaleY = 1.1;
                setTimeout(() => {
                    ball.scaleX = 1; ball.scaleY = 1;
                    ball.squishing = false;
                }, 90);
            }, 130);
        }

        // ── Main rAF loop ─────────────────────────────────────────────
        function tick() {
            const W = window.innerWidth;
            const H = window.innerHeight;

            for (const b of balls) {
                b.x += b.vx;
                b.y += b.vy;

                if (b.x <= 0) { b.x = 0; b.vx = Math.abs(b.vx); squish(b, 0.5, 1.5); }
                else if (b.x + b.size >= W) { b.x = W - b.size; b.vx = -Math.abs(b.vx); squish(b, 0.5, 1.5); }

                if (b.y <= 0) { b.y = 0; b.vy = Math.abs(b.vy); squish(b, 1.5, 0.5); }
                else if (b.y + b.size >= H) { b.y = H - b.size; b.vy = -Math.abs(b.vy); squish(b, 1.5, 0.5); }

                b.el.style.transform = `translate(${b.x}px,${b.y}px) scale(${b.scaleX},${b.scaleY})`;
            }

            requestAnimationFrame(tick);
        }

        requestAnimationFrame(tick);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();

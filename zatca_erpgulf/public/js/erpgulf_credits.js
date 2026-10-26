// Copyright (c) ERPGulf (https://erpgulf.com). All rights reserved.
// ERPGulf credits for Help → About: "<App title> … from ERPGulf.com" (with link).
// Same file in every ERPGulf app: the app is detected from this script's path.
// Works with the Frappe v15 and v16 About dialogs.
(function () {
    const CREDIT_TEXT = "ERPGulf.com";
    const CREDIT_URL = "https://erpgulf.com";

    const src = (document.currentScript && document.currentScript.src) || "";
    const match = src.match(/\/assets\/([^/]+)\//);
    if (!match) return;

    // register this app; all ERPGulf apps share one list and one watcher
    window.erpgulf_credit_apps = window.erpgulf_credit_apps || new Set();
    window.erpgulf_credit_apps.add(match[1]);
    if (window.erpgulf_credit_started) return;
    window.erpgulf_credit_started = true;

    function make_credit() {
        const credit = document.createElement("span");
        credit.className = "erpgulf-credit";
        credit.innerHTML =
            ` <span class="text-muted">from</span> ` +
            `<a href="${CREDIT_URL}" target="_blank" rel="noopener noreferrer">${CREDIT_TEXT}</a>`;
        // v16: clicking the row copies the version; let the link open instead
        credit.querySelector("a").addEventListener("click", (e) => e.stopPropagation());
        return credit;
    }

    function add_credits() {
        const list = document.getElementById("about-app-versions");
        if (!list) return;

        window.erpgulf_credit_apps.forEach((app) => {
            // Frappe v16: one row per app, title attribute "<app>: <version>"
            const row = list.querySelector(`.about-app-row[title^="${app}:"]`);
            if (row) {
                const name = row.querySelector(".about-app-name");
                if (name && !name.querySelector(".erpgulf-credit")) name.appendChild(make_credit());
                return;
            }

            // Frappe v15: one line per app, "<b>App Title:</b> vX (branch)"
            const versions = window.frappe && frappe.versions;
            const title = versions && versions[app] && versions[app].title;
            if (!title) return;
            list.querySelectorAll("p").forEach((p) => {
                const b = p.querySelector("b");
                if (b && b.textContent.trim() === `${title}:` && !p.querySelector(".erpgulf-credit")) {
                    p.insertBefore(make_credit(), p.querySelector("br"));
                }
            });
        });
    }

    function start() {
        new MutationObserver(add_credits).observe(document.body, { childList: true, subtree: true });
        add_credits();
    }

    if (document.body) start();
    else document.addEventListener("DOMContentLoaded", start);
})();
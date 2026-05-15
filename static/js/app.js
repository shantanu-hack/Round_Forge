(function () {

    /* ═══════════════════════════════════════════════
       TIMER & ROUND INFO
    ════════════════════════════════════════════════*/
    const timerRoot = document.querySelector("[data-timer-root]");
    if (!timerRoot) return;

    const timerEl       = document.getElementById("simTimer");
    const display       = timerRoot.querySelector("[data-timer-display]");
    const timeInputs    = timerRoot.querySelectorAll("[data-time-input]");
    const expireForm    = timerRoot.querySelector("[data-expire-form]");
    const ringFill      = document.getElementById("timerRingFill");
    const durationDisplay = document.getElementById("roundDurationDisplay");

    if (!display) return;

    const totalSeconds  = timerEl ? Number(timerEl.dataset.remainingSeconds || 0) : 0;
    const startedAt     = Date.now();
    const CIRCUMFERENCE = 213.6; // 2π × 34 (Radius updated to 34 for 2x size)
    let   expirySubmitted = false;

    // Display initial total round duration
    if (durationDisplay && totalSeconds > 0) {
        const totalMins = Math.ceil(totalSeconds / 60);
        durationDisplay.textContent = `Round duration: ${totalMins} minutes`;
    }

    function lockAnswerForms() {
        timerRoot.querySelectorAll(".answer-form textarea, .answer-form button, .btn-submit").forEach(el => {
            el.disabled = true;
        });
    }

    function submitExpiry() {
        if (expirySubmitted || !expireForm) return;
        expirySubmitted = true;
        lockAnswerForms();
        expireForm.submit();
    }

    function renderTimer() {
        const elapsed   = Math.floor((Date.now() - startedAt) / 1000);
        const remaining = Math.max(0, totalSeconds - elapsed);
        const mm = Math.floor(remaining / 60);
        const ss = String(remaining % 60).padStart(2, "0");

        display.textContent = `${mm}:${ss}`;
        timeInputs.forEach(inp => { inp.value = String(elapsed); });

        // Ring progress
        if (ringFill && totalSeconds > 0) {
            const fraction   = remaining / totalSeconds;
            const dashOffset = CIRCUMFERENCE * (1 - fraction);
            ringFill.style.strokeDashoffset = String(dashOffset);
        }

        // Urgency
        if (remaining <= 60 && timerEl) {
            timerEl.classList.add("timer--urgent");
            if (ringFill) ringFill.classList.add("timer-ring-fill--urgent");
        }

        if (remaining <= 0) submitExpiry();
    }

    renderTimer();
    setInterval(renderTimer, 1000);

    /* ═══════════════════════════════════════════════
       ONE-QUESTION CAROUSEL & PROGRESS LINE
    ════════════════════════════════════════════════*/
    const carousel = document.getElementById("questionCarousel");
    if (!carousel) return;

    const cards      = Array.from(carousel.querySelectorAll(".q-card"));
    const pips       = Array.from(document.querySelectorAll(".spt-node"));
    const lineActive = document.getElementById("sptLineActive");
    const total      = cards.length;
    const answeredRaw = carousel.dataset.answeredIds || "";
    const answeredIds = new Set(
        answeredRaw.split(",").map(s => s.trim()).filter(Boolean)
    );

    let current = 0;
    const firstUnanswered = cards.findIndex(
        c => !answeredIds.has(c.dataset.questionId)
    );
    current = firstUnanswered >= 0 ? firstUnanswered : Math.max(0, total - 1);

    function syncPips(index) {
        pips.forEach((pip, i) => {
            pip.classList.toggle("spt-node--active", i === index);
            if (answeredIds.has(cards[i].dataset.questionId)) {
                pip.classList.add("spt-node--done");
            }
        });

        // Animate the progression line connecting the nodes
        if (lineActive && total > 1) {
            const percentage = (index / (total - 1)) * 100;
            lineActive.style.width = `${percentage}%`;
        }
    }

    function showCard(index, direction) {
        const prev = cards.findIndex(c => c.classList.contains("is-active"));

        if (prev >= 0 && prev !== index) {
            cards[prev].classList.add("is-exit");
            setTimeout(() => {
                cards[prev].classList.remove("is-active", "is-exit");
                cards[prev].setAttribute("aria-hidden", "true");
            }, 180);
        }

        setTimeout(() => {
            cards[index].classList.add("is-active");
            cards[index].setAttribute("aria-hidden", "false");
        }, prev >= 0 && prev !== index ? 100 : 0);

        syncPips(index);
        updateNavButtons(index);
    }

    function updateNavButtons(index) {
        carousel.querySelectorAll("[data-prev]").forEach(btn => {
            btn.disabled = (index === 0);
        });
        carousel.querySelectorAll("[data-next]").forEach(btn => {
            btn.disabled = (index === total - 1);
        });
    }

    // Delegate nav clicks
    carousel.addEventListener("click", e => {
        if (e.target.closest("[data-prev]") && current > 0) {
            current--;
            showCard(current);
        }
        if (e.target.closest("[data-next]") && current < total - 1) {
            current++;
            showCard(current);
        }
    });

    // Keyboard navigation
    document.addEventListener("keydown", e => {
        const tag = document.activeElement.tagName;
        if (tag === "TEXTAREA" || tag === "INPUT") return;
        if (e.key === "ArrowLeft"  && current > 0)        { current--; showCard(current); }
        if (e.key === "ArrowRight" && current < total - 1) { current++; showCard(current); }
    });

    // Auto-grow textareas
    carousel.querySelectorAll("textarea[data-autogrow]").forEach(ta => {
        ta.addEventListener("input", () => {
            ta.style.height = "auto";
            ta.style.height = ta.scrollHeight + "px";
        });
    });

    showCard(current);

    /* ═══════════════════════════════════════════════
       INLINE SUBMISSION & EVALUATION OVERLAY
    ════════════════════════════════════════════════*/
    const evalOverlay  = document.getElementById("evalOverlay");
    const evalStatus   = document.getElementById("evalStatus");
    const evalStepEls  = document.querySelectorAll(".eval-step");

    const EVAL_SEQUENCE = [
        { text: "Aggregating responses...", delay: 0 },
        { text: "Cross-referencing technical benchmarks...", delay: 1800 },
        { text: "Generating readiness profile...", delay: 3600 },
    ];

    function showEvalOverlay() {
        if (!evalOverlay) return;
        document.body.classList.add("sim-evaluating");
        evalOverlay.classList.add("is-visible");
        evalOverlay.setAttribute("aria-hidden", "false");

        EVAL_SEQUENCE.forEach((step, i) => {
            setTimeout(() => {
                if (evalStatus) evalStatus.textContent = "Processing Simulation Data";
                evalStepEls.forEach((el, j) => {
                    el.classList.toggle("eval-step--active", j === i);
                    if (j < i) el.classList.add("eval-step--completed");
                });
            }, step.delay);
        });
    }

    carousel.querySelectorAll(".answer-form[data-answer-form]").forEach(form => {
        if (form.dataset.rfSubmitBound === "true") return;
        form.dataset.rfSubmitBound = "true";

        form.addEventListener("submit", (e) => {
            e.preventDefault(); // Intercept default submission to show inline feedback

            if (form.dataset.submitting === "true") return;

            const activeCard = form.closest(".q-card");
            if (activeCard && !activeCard.classList.contains("is-active")) {
                const activeIndex = cards.indexOf(activeCard);
                if (activeIndex >= 0) {
                    current = activeIndex;
                    showCard(current);
                }
                return;
            }

            const textarea = form.querySelector("textarea[name='answer_text']");
            const minLength = Number(textarea?.getAttribute("minlength") || 20);
            const answerText = (textarea?.value || "").trim();

            if (!textarea || answerText.length < minLength) {
                if (textarea) {
                    textarea.setCustomValidity("Answer must be at least 20 characters for a meaningful evaluation.");
                    textarea.reportValidity();
                    textarea.addEventListener("input", () => textarea.setCustomValidity(""), { once: true });
                    textarea.focus();
                }
                return;
            }

            textarea.setCustomValidity("");
            form.dataset.submitting = "true";

            const qId    = form.querySelector("[name='question_id']").value;
            const isLast = isLastUnanswered(qId);
            
            const navActions = form.querySelector('.q-nav-actions');
            const miniNextMsg = form.querySelector('#miniNextMsg');

            // Lock input without disabling it; disabled fields are omitted from POST.
            textarea.readOnly = true;
            form.querySelectorAll("button").forEach(btn => {
                btn.disabled = true;
            });

            // Hide controls for a quiet submit transition. The final answer still opens the evaluation overlay.
            if (navActions) navActions.style.display = 'none';
            if (miniNextMsg && !isLast) {miniNextMsg.classList.add("is-visible");}

            // Execute submission after smooth delay
            setTimeout(() => {
                if (isLast) {
                    showEvalOverlay();
                    setTimeout(() => { form.submit(); }, 600); // Allow overlay to fade in before page unloads
                } else {
                    form.submit();
                }
            }, 1800); // Wait 1.8s for the inline success animation to finish
        });
    });

    function isLastUnanswered(submittedId) {
        const unanswered = cards.filter(
            c => !answeredIds.has(c.dataset.questionId) &&
                 c.dataset.questionId !== String(submittedId)
        );
        return unanswered.length === 0;
    }

    /* ═══════════════════════════════════════════════
       CINEMATIC ROUND RESULT OVERLAY
    ════════════════════════════════════════════════*/
    const resultOverlay   = document.getElementById("resultOverlay");
    const resultPanel     = document.getElementById("resultPanel");
    const resultGlyph     = document.getElementById("resultGlyph");
    const resultVerdict   = document.getElementById("resultVerdict");
    const resultHeading   = document.getElementById("resultHeading");
    const resultSub       = document.getElementById("resultSub");
    const resultScoreFill = document.getElementById("resultScoreFill");
    const resultScoreWrap = document.getElementById("resultScoreWrap");
    const resultScoreLabel = document.getElementById("resultScoreLabel");
    const resultActions   = document.getElementById("resultActions");

    const body = document.body;
    const roundResult = body.dataset.roundResult;
    const roundClearedModal = document.getElementById("roundClearedModal");
    const continueNextRound = document.getElementById("continueNextRound");

    if (roundResult === "pass" && roundClearedModal) {
        showRoundClearedModal();
    } else if (roundResult && resultOverlay) {
        const score     = parseInt(body.dataset.roundScore || "0", 10);
        const roundName = body.dataset.roundName || "";
        const nextRound = body.dataset.nextRound || "";
        const isPass    = roundResult === "pass";

        renderResultOverlay({ isPass, score, roundName, nextRound });
    }

    function showRoundClearedModal() {
        document.body.classList.add("sim-evaluating");
        requestAnimationFrame(() => {
            roundClearedModal.classList.add("is-visible");
            roundClearedModal.setAttribute("aria-hidden", "false");
            if (continueNextRound) continueNextRound.focus();
        });

        if (continueNextRound) {
            continueNextRound.addEventListener("click", () => {
                continueNextRound.disabled = true;
                const continueUrl = roundClearedModal.dataset.continueUrl || window.location.href;
                window.location.assign(continueUrl);
            });
        }
    }

    function renderResultOverlay({ isPass, score, roundName, nextRound }) {
        if (!resultOverlay) return;

        // Cinematic Glyph
        resultGlyph.className = "result-glyph " + (isPass ? "result-glyph--pass" : "result-glyph--fail");
        resultGlyph.innerHTML = isPass
            ? `<svg width="40" height="40" viewBox="0 0 24 24" fill="none">
                   <path d="M5 12l4.5 4.5 9.5-9.5" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
               </svg>`
            : `<svg width="40" height="40" viewBox="0 0 24 24" fill="none">
                   <path d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"/>
               </svg>`;

        resultVerdict.className = "result-verdict " + (isPass ? "result-verdict--pass" : "result-verdict--fail");
        resultVerdict.textContent = isPass ? "ROUND CLEARED" : "MORE PRACTICE RECOMMENDED";
        
        resultHeading.textContent = isPass 
            ? `${roundName} Benchmark Passed` 
            : `${roundName} Benchmark Not Yet Cleared`;
            
        resultSub.textContent = isPass
            ? (nextRound ? `Preparing ${nextRound} Evaluation...` : "Finalizing readiness profile...")
            : "Review your readiness report to identify core focus areas before attempting this simulation again.";

        if (resultScoreWrap) {
            resultScoreFill.className = "result-score-fill " + (isPass ? "result-score-fill--pass" : "result-score-fill--fail");
            if (resultScoreLabel) {
                resultScoreLabel.innerHTML = isPass 
                    ? `Technical Score: <strong style="color:var(--success); font-size: 1.2em">${score}%</strong>` 
                    : `Current Score: <strong style="color:var(--danger); font-size: 1.2em">${score}%</strong>`;
            }
            setTimeout(() => {
                resultScoreFill.style.width = score + "%";
            }, 800); 
        }

        resultActions.innerHTML = "";
        if (!isPass) {
            const retryBtn = document.createElement("button");
            retryBtn.className = "btn-ghost";
            retryBtn.textContent = "Retry Simulation";
            retryBtn.addEventListener("click", () => {
                document.querySelector("form[action*='retry']")?.submit();
            });
            resultActions.appendChild(retryBtn);
        }

        const continueBtn = document.createElement("button");
        continueBtn.className = "btn-primary";
        continueBtn.textContent = isPass ? "Continue" : "View Readiness Report";
        continueBtn.addEventListener("click", () => {
            resultOverlay.classList.remove("is-visible");
            document.body.classList.remove("sim-evaluating");
            if (!isPass) {
                document.querySelector("a[href*='reports']")?.click();
            }
        });
        
        // Hide button initially for automatic flow on pass
        if(isPass) continueBtn.style.display = "none";
        resultActions.appendChild(continueBtn);

        // Show Overlay with cinematic timing
        setTimeout(() => {
            document.body.classList.add("sim-evaluating");
            resultOverlay.classList.add("is-visible");
            resultOverlay.setAttribute("aria-hidden", "false");
        }, 150);

        // Automatic cinematic progression for Passes
        if (isPass) {
            setTimeout(() => {
                resultSub.classList.add("pulse-text");
            }, 2500);

            setTimeout(() => {
                continueBtn.click();
            }, 4500); // Fullscreen immersive delay
        }
    }

    /* ═══════════════════════════════════════════════
       FOCUS MODE: subtle rail dim on typing
    ════════════════════════════════════════════════*/
    const rail = document.getElementById("simRail");

    timerRoot.addEventListener("focusin", e => {
        if (e.target.tagName === "TEXTAREA" && rail) {
            rail.style.opacity = "0.3";
            rail.style.transition = "opacity 0.5s ease";
        }
    });

    timerRoot.addEventListener("focusout", e => {
        if (e.target.tagName === "TEXTAREA" && rail) {
            rail.style.opacity = "";
        }
    });

})();

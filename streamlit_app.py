"""BuyWise AI — Streamlit dashboard over the FastAPI price-intelligence backend."""

from __future__ import annotations

import html
import os
from datetime import datetime
from typing import Any, Literal

import requests
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000").rstrip("/")

REQUEST_TIMEOUT = 15
AGENT_TIMEOUT = 120
HEALTH_TIMEOUT = 3

CURRENCY_SYMBOLS = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}

VERDICTS: dict[str, dict[str, str]] = {
    "BUY": {
        "label": "Buy now",
        "icon": "✅",
        "accent": "#22C55E",
        "tint": "rgba(34, 197, 94, 0.12)",
        "blurb": "Prices and seller terms both check out.",
    },
    "WAIT": {
        "label": "Hold off",
        "icon": "⏳",
        "accent": "#F59E0B",
        "tint": "rgba(245, 158, 11, 0.12)",
        "blurb": "Not the moment — the agent expects a better one.",
    },
    "RE-EVALUATE": {
        "label": "Re-evaluate",
        "icon": "🔍",
        "accent": "#FB7185",
        "tint": "rgba(251, 113, 133, 0.12)",
        "blurb": "Something about this listing needs a second look.",
    },
    "unable_to_decide": {
        "label": "No decision",
        "icon": "🤷",
        "accent": "#94A3B8",
        "tint": "rgba(148, 163, 184, 0.12)",
        "blurb": "The agent could not reach a confident call.",
    },
}

EXAMPLE_PROMPTS = [
    "Should I buy variant_id=1?",
    "Is variant_id=2 a good deal right now, and what is the return policy?",
    "Compare the offers for variant_id=1 and tell me whether to wait.",
]

CSS = """
<style>
:root {
--bw-line: rgba(148, 163, 184, 0.18);
--bw-muted: #93A2BA;
--bw-accent: #2DD4BF;
}
.block-container { padding-top: 2.4rem; max-width: 1180px; }
#MainMenu, footer { visibility: hidden; }

@keyframes bwRise {
from { opacity: 0; transform: translateY(14px); }
to { opacity: 1; transform: translateY(0); }
}
@keyframes bwGlow {
0%, 100% { box-shadow: 0 0 0 0 var(--bw-glow); }
50% { box-shadow: 0 0 0 14px rgba(0, 0, 0, 0); }
}

.bw-hero {
background: linear-gradient(120deg, #10233A 0%, #14304A 45%, #0F2E36 100%);
border: 1px solid var(--bw-line);
border-radius: 18px;
padding: 1.6rem 1.9rem;
margin-bottom: 1.6rem;
animation: bwRise 0.5s ease both;
}
.bw-hero h1 { font-size: 1.9rem; font-weight: 700; margin: 0; letter-spacing: -0.02em; }
.bw-hero p { color: var(--bw-muted); margin: 0.45rem 0 0; font-size: 0.95rem; }
.bw-hero .bw-kicker {
color: var(--bw-accent); font-size: 0.72rem; font-weight: 700;
letter-spacing: 0.18em; text-transform: uppercase; margin-bottom: 0.5rem;
}

.bw-card {
background: #141E31;
border: 1px solid var(--bw-line);
border-radius: 14px;
padding: 1.05rem 1.15rem;
margin-bottom: 0.9rem;
transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
animation: bwRise 0.4s ease both;
}
.bw-card:hover {
transform: translateY(-3px);
border-color: rgba(45, 212, 191, 0.45);
box-shadow: 0 10px 26px rgba(0, 0, 0, 0.35);
}
.bw-card.bw-best { border-color: rgba(45, 212, 191, 0.55); background: #12253A; }

.bw-row { display: flex; align-items: center; justify-content: space-between; gap: 0.5rem; }
.bw-seller { font-weight: 600; font-size: 0.95rem; }
.bw-price { font-size: 1.65rem; font-weight: 700; letter-spacing: -0.02em; margin: 0.5rem 0 0.35rem; }
.bw-meta { color: var(--bw-muted); font-size: 0.8rem; line-height: 1.55; }
.bw-link { color: var(--bw-accent); font-size: 0.82rem; text-decoration: none; }
.bw-link:hover { text-decoration: underline; }

.bw-badge {
display: inline-block; padding: 0.16rem 0.55rem; border-radius: 999px;
font-size: 0.68rem; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase;
}
.bw-badge-ok { background: rgba(34, 197, 94, 0.15); color: #4ADE80; }
.bw-badge-off { background: rgba(251, 113, 133, 0.15); color: #FB7185; }
.bw-badge-neutral { background: rgba(148, 163, 184, 0.15); color: #B6C2D6; }
.bw-badge-best { background: rgba(45, 212, 191, 0.18); color: #5EEAD4; }

.bw-verdict {
border-radius: 18px; padding: 1.5rem 1.7rem; margin: 0.4rem 0 1.1rem;
border: 1px solid var(--bw-accent-c); background: var(--bw-tint);
animation: bwRise 0.55s cubic-bezier(0.22, 1, 0.36, 1) both, bwGlow 2.4s ease-out 0.4s 2;
}
.bw-verdict .bw-v-top { display: flex; align-items: center; gap: 0.75rem; }
.bw-verdict .bw-v-icon { font-size: 2rem; line-height: 1; }
.bw-verdict .bw-v-label { font-size: 1.75rem; font-weight: 800; color: var(--bw-accent-c); letter-spacing: -0.02em; }
.bw-verdict .bw-v-blurb { color: var(--bw-muted); font-size: 0.88rem; margin-top: 0.15rem; }
.bw-verdict .bw-v-reason {
margin-top: 1.05rem; padding-top: 1rem; border-top: 1px solid var(--bw-line);
font-size: 0.97rem; line-height: 1.65; white-space: pre-wrap;
}

.bw-chunk-text { font-size: 0.95rem; line-height: 1.65; margin-top: 0.6rem; white-space: pre-wrap; }
.bw-empty {
border: 1px dashed var(--bw-line); border-radius: 14px; padding: 2.2rem 1rem;
text-align: center; color: var(--bw-muted); font-size: 0.9rem;
}
.bw-status { font-size: 0.82rem; color: var(--bw-muted); }
.bw-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
</style>
"""


class ApiError(Exception):
    """A backend call failed in a way the user should see a clean message for."""


def _friendly_http_error(response: requests.Response) -> str:
    detail: Any = None
    try:
        payload = response.json()
        if isinstance(payload, dict):
            detail = payload.get("detail")
    except ValueError:
        detail = None

    if isinstance(detail, list):
        # FastAPI validation errors come back as a list of error objects.
        detail = "; ".join(str(item.get("msg", item)) for item in detail if isinstance(item, dict)) or None
    if detail is not None:
        return str(detail)

    if response.status_code >= 500:
        return "The backend hit an internal error. Check the uvicorn logs for details."
    return f"The backend rejected the request (HTTP {response.status_code})."


def api_call(
    method: Literal["GET", "POST"],
    path: str,
    *,
    payload: dict[str, Any] | None = None,
    auth: bool = False,
    timeout: int = REQUEST_TIMEOUT,
) -> Any:
    """Single choke point for backend traffic — every failure becomes an ApiError."""
    headers = {}
    if auth:
        token = st.session_state.get("token")
        if not token:
            raise ApiError("You need to be logged in for this action.")
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = requests.request(method, f"{API_BASE_URL}{path}", json=payload, headers=headers, timeout=timeout)
    except requests.exceptions.Timeout:
        raise ApiError(f"The backend did not respond within {timeout}s. It may still be working — try again.")
    except requests.exceptions.ConnectionError:
        raise ApiError(f"Could not reach the API at {API_BASE_URL}. Is `uvicorn main:app --reload` running?")
    except requests.exceptions.RequestException:
        raise ApiError("The request to the backend could not be completed.")

    if not response.ok:
        raise ApiError(_friendly_http_error(response))

    try:
        return response.json()
    except ValueError:
        raise ApiError("The backend returned a response that was not valid JSON.")


def signup_user(username: str, password: str) -> dict[str, Any]:
    return api_call("POST", "/auth/signup", payload={"username": username, "password": password})


def login_user(username: str, password: str) -> dict[str, Any]:
    return api_call("POST", "/auth/login", payload={"username": username, "password": password})


def search_products_by_name(query: str, limit: int = 20) -> list[dict[str, Any]]:
    return api_call("GET", f"/products/search?q={requests.utils.quote(query)}&limit={limit}")


def fetch_variant_offers(variant_id: int) -> list[dict[str, Any]]:
    return api_call("POST", "/search", payload={"variant_id": variant_id})


def fetch_product_offers(product_id: int) -> list[dict[str, Any]]:
    return api_call("GET", f"/products/{product_id}/offers")


def fetch_product_variants(product_id: int) -> list[dict[str, Any]]:
    return api_call("GET", f"/products/{product_id}/variants")


def create_watchlist_entry(variant_id: int, target_price: float | None) -> dict[str, Any]:
    return api_call(
        "POST",
        "/watchlist",
        payload={"variant_id": variant_id, "target_price": target_price},
        auth=True,
    )


def fetch_my_watchlist() -> list[dict[str, Any]]:
    return api_call("GET", "/watchlist", auth=True)


def create_seller_policy(
    seller_id: int,
    policy_type: str,
    category: str | None,
    policy_text: str,
    source_url: str | None,
) -> dict[str, Any]:
    return api_call(
        "POST",
        "/seller-policies",
        payload={
            "seller_id": seller_id,
            "policy_type": policy_type,
            "category": category,
            "policy_text": policy_text,
            "source_url": source_url,
        },
    )


def search_seller_policies(query: str, n_results: int, seller_id: int | None) -> list[dict[str, Any]]:
    return api_call(
        "POST",
        "/seller-policies/search",
        payload={"query": query, "n_results": n_results, "seller_id": seller_id},
    )


def ask_agent(message: str) -> dict[str, Any]:
    return api_call("POST", "/agent", payload={"message": message}, auth=True, timeout=AGENT_TIMEOUT)


@st.cache_data(ttl=20, show_spinner=False)
def backend_is_reachable(base_url: str) -> bool:
    """FastAPI always serves /openapi.json, so it doubles as a liveness probe."""
    try:
        return requests.get(f"{base_url}/openapi.json", timeout=HEALTH_TIMEOUT).ok
    except requests.exceptions.RequestException:
        return False


def money(amount: float, currency: str) -> str:
    symbol = CURRENCY_SYMBOLS.get(currency.upper())
    return f"{symbol}{amount:,.2f}" if symbol else f"{currency} {amount:,.2f}"


def pretty_timestamp(raw: str | None) -> str:
    if not raw:
        return "unknown"
    try:
        return datetime.fromisoformat(raw).strftime("%d %b %Y, %H:%M")
    except (TypeError, ValueError):
        return str(raw)


def availability_badge(availability: str) -> str:
    label = availability.replace("_", " ").title()
    if availability == "in_stock":
        return f'<span class="bw-badge bw-badge-ok">{html.escape(label)}</span>'
    if availability == "out_of_stock":
        return f'<span class="bw-badge bw-badge-off">{html.escape(label)}</span>'
    return f'<span class="bw-badge bw-badge-neutral">{html.escape(label)}</span>'


def hero(kicker: str, title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="bw-hero"><div class="bw-kicker">{html.escape(kicker)}</div>'
        f"<h1>{html.escape(title)}</h1><p>{html.escape(subtitle)}</p></div>",
        unsafe_allow_html=True,
    )


def empty_state(message: str) -> None:
    st.markdown(f'<div class="bw-empty">{html.escape(message)}</div>', unsafe_allow_html=True)


def require_login() -> bool:
    if st.session_state.get("token"):
        return True
    empty_state("Log in from the sidebar to use this section.")
    return False


def render_offer_card(offer: dict[str, Any], is_best: bool) -> None:
    link = ""
    if offer.get("product_url"):
        url = html.escape(str(offer["product_url"]), quote=True)
        link = f'<div style="margin-top:0.55rem"><a class="bw-link" href="{url}" target="_blank">Open listing ↗</a></div>'

    best_badge = '<span class="bw-badge bw-badge-best">Best price</span>' if is_best else ""

    seller_name = html.escape(str(offer.get("seller_name") or f"Seller #{offer['seller_id']}"))

    st.markdown(
        f'<div class="bw-card{" bw-best" if is_best else ""}">'
        f'<div class="bw-row"><span class="bw-seller">{seller_name}</span>{best_badge}</div>'
        f'<div class="bw-price">{html.escape(money(offer["current_price"], offer["currency"]))}</div>'
        f'<div class="bw-row">{availability_badge(offer["availability"])}</div>'
        f'<div class="bw-meta" style="margin-top:0.55rem">Last checked {html.escape(pretty_timestamp(offer.get("last_checked_at")))}</div>'
        f"{link}</div>",
        unsafe_allow_html=True,
    )


def render_offer_results(offers: list[dict[str, Any]]) -> None:
    if not offers:
        empty_state("No eligible offers came back for that id. Try a different one.")
        return

    prices = [offer["current_price"] for offer in offers]
    currency = offers[0]["currency"]
    best = min(prices)
    average = sum(prices) / len(prices)

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("Offers", len(offers))
    col_b.metric(
        "Best price",
        money(best, currency),
        delta=f"{best - average:,.2f} vs avg" if len(offers) > 1 else None,
        delta_color="inverse",
    )
    col_c.metric("Highest price", money(max(prices), currency))
    col_d.metric("Spread", money(max(prices) - best, currency))

    st.markdown("")
    ranked = sorted(offers, key=lambda offer: offer["current_price"])
    columns = st.columns(3)
    for index, offer in enumerate(ranked):
        with columns[index % 3]:
            render_offer_card(offer, is_best=offer["current_price"] == best)


def render_product_match_card(product: dict[str, Any]) -> None:
    brand = product.get("brand") or "Unknown brand"
    category = product.get("category") or "Uncategorized"
    st.markdown(
        f'<div class="bw-card"><div class="bw-row">'
        f'<span class="bw-seller">{html.escape(product["name"])}</span>'
        f'<span class="bw-badge bw-badge-neutral">{html.escape(category)}</span></div>'
        f'<div class="bw-meta" style="margin-top:0.45rem">{html.escape(brand)} · Product #{product["product_id"]}</div>'
        f"</div>",
        unsafe_allow_html=True,
    )


def page_price_search() -> None:
    hero(
        "Price search",
        "Live offers across sellers",
        "Just search for the product you're after.",
    )

    query = st.text_input("Product name", placeholder="iPhone, Galaxy S24, MacBook…", key="search_name_query")
    submitted = st.button("Search products", type="primary", key="name_search_btn")

    if submitted:
        if not query.strip():
            st.warning("Type part of a product name first.")
        else:
            with st.spinner("Searching the catalog…"):
                try:
                    st.session_state["name_matches"] = search_products_by_name(query.strip())
                except ApiError as error:
                    st.session_state.pop("name_matches", None)
                    st.error(str(error))

    matches = st.session_state.get("name_matches")
    if matches is not None:
        if not matches:
            empty_state("No products matched that name. Try a shorter or different term.")
        else:
            st.caption(f"{len(matches)} product(s) matched")
            for product in matches:
                card_col, button_col = st.columns([4, 1], vertical_alignment="center")
                with card_col:
                    render_product_match_card(product)
                with button_col:
                    if st.button("View offers", key=f"select_product_{product['product_id']}", use_container_width=True):
                        st.session_state["selected_product_id"] = product["product_id"]
                        st.session_state["selected_product_name"] = product["name"]

    selected_id = st.session_state.get("selected_product_id")
    if selected_id is not None:
        st.markdown("")
        st.subheader(f"Offers for {st.session_state.get('selected_product_name', 'selected product')}")
        with st.spinner("Loading offers…"):
            try:
                offers = fetch_product_offers(int(selected_id))
            except ApiError as error:
                st.error(str(error))
            else:
                render_offer_results(offers)

    with st.expander("Advanced: look up by internal ID"):
        st.caption("Not needed for normal use — this is a debugging shortcut for known variant/product ids.")
        left, right = st.columns([3, 1], vertical_alignment="bottom")
        variant_id = left.number_input("Variant ID", min_value=1, step=1, value=1, key="search_variant_id")
        variant_submitted = right.button("Search by variant ID", use_container_width=True)

        if variant_submitted:
            with st.spinner("Fetching offers…"):
                try:
                    st.session_state["variant_offers"] = fetch_variant_offers(int(variant_id))
                except ApiError as error:
                    st.session_state.pop("variant_offers", None)
                    st.error(str(error))

        if "variant_offers" in st.session_state:
            render_offer_results(st.session_state["variant_offers"])


def render_verdict(decision: str, reasoning: str) -> None:
    style = VERDICTS.get(decision, VERDICTS["unable_to_decide"])
    st.markdown(
        f'<div class="bw-verdict" style="--bw-accent-c:{style["accent"]};--bw-tint:{style["tint"]};'
        f'--bw-glow:{style["tint"]}">'
        f'<div class="bw-v-top"><span class="bw-v-icon">{style["icon"]}</span><div>'
        f'<div class="bw-v-label">{html.escape(style["label"])}</div>'
        f'<div class="bw-v-blurb">{html.escape(style["blurb"])}</div></div></div>'
        f'<div class="bw-v-reason">{html.escape(reasoning)}</div></div>',
        unsafe_allow_html=True,
    )


def page_agent() -> None:
    hero(
        "Decision agent",
        "Ask before you buy",
        "The agent calls the offer and policy tools itself, then commits to BUY, WAIT or RE-EVALUATE.",
    )

    if not require_login():
        return

    st.caption("Start from an example")
    for column, prompt in zip(st.columns(len(EXAMPLE_PROMPTS)), EXAMPLE_PROMPTS):
        if column.button(prompt, use_container_width=True, key=f"example_{prompt}"):
            st.session_state["agent_prompt"] = prompt

    message = st.text_area(
        "Your question",
        key="agent_prompt",
        height=110,
        placeholder="Should I buy variant_id=1?",
    )

    if st.button("Ask the agent", type="primary", disabled=not message.strip()):
        with st.spinner("Agent is calling tools and weighing the offers…"):
            try:
                result = ask_agent(message.strip())
            except ApiError as error:
                st.session_state.pop("agent_result", None)
                st.error(str(error))
            else:
                st.session_state["agent_result"] = result
                decision = result.get("decision", "unable_to_decide")
                if decision == "BUY":
                    st.balloons()
                    st.toast("The agent says buy it", icon="✅")
                elif decision == "WAIT":
                    st.toast("The agent says wait", icon="⏳")
                elif decision == "RE-EVALUATE":
                    st.toast("The agent wants another look", icon="🔍")
                else:
                    st.toast("No confident decision", icon="🤷")

    result = st.session_state.get("agent_result")
    if result:
        render_verdict(result.get("decision", "unable_to_decide"), result.get("reasoning", ""))
    else:
        empty_state("Ask a question above and the verdict will appear here.")


def variant_label(variant: dict[str, Any]) -> str:
    attributes = variant.get("attributes") or {}
    if attributes:
        return " · ".join(str(value) for value in attributes.values())
    if variant.get("sku"):
        return str(variant["sku"])
    return f"Variant #{variant['variant_id']}"


def page_watchlist() -> None:
    hero(
        "Watchlist",
        "Track a product's price",
        "Search for the product, pick the exact version, and set a target price to watch for.",
    )

    if not require_login():
        return

    left, right = st.columns([1.15, 1], gap="large")

    with left:
        query = st.text_input("Product name", placeholder="iPhone, Galaxy S24, MacBook…", key="wl_name_query")
        if st.button("Search", key="wl_search_btn"):
            if not query.strip():
                st.warning("Type part of a product name first.")
            else:
                with st.spinner("Searching the catalog…"):
                    try:
                        st.session_state["wl_matches"] = search_products_by_name(query.strip())
                    except ApiError as error:
                        st.session_state.pop("wl_matches", None)
                        st.error(str(error))

        matches = st.session_state.get("wl_matches")
        if matches is not None:
            if not matches:
                empty_state("No products matched that name. Try a shorter or different term.")
            else:
                options = {f"{m['name']} ({m.get('brand') or 'Unknown brand'})": m["product_id"] for m in matches}
                choice = st.selectbox("Which product?", list(options), key="wl_product_choice")
                product_id = options[choice]

                with st.spinner("Loading versions…"):
                    try:
                        variants = fetch_product_variants(product_id)
                    except ApiError as error:
                        variants = []
                        st.error(str(error))

                if not variants:
                    empty_state("This product has no variants yet.")
                else:
                    variant_options = {variant_label(v): v["variant_id"] for v in variants}
                    variant_choice = st.selectbox("Which version?", list(variant_options), key="wl_variant_choice")
                    variant_id = variant_options[variant_choice]

                    with st.form("watchlist_form"):
                        target_price = st.number_input(
                            "Target price",
                            min_value=0.0,
                            step=100.0,
                            value=None,
                            help="Optional — leave blank to watch the variant without a price trigger.",
                        )
                        submitted = st.form_submit_button("Add to watchlist", type="primary", use_container_width=True)

                    if submitted:
                        with st.spinner("Saving to the watchlist…"):
                            try:
                                create_watchlist_entry(
                                    int(variant_id),
                                    float(target_price) if target_price is not None else None,
                                )
                            except ApiError as error:
                                st.error(str(error))
                            else:
                                st.session_state.pop("my_watchlist", None)
                                st.toast("Added to the watchlist", icon="📌")
                                st.success(f"Watching {choice} — {variant_choice}.")

    with right:
        st.caption("Your watchlist")
        if st.button("Refresh", key="wl_refresh_btn"):
            st.session_state.pop("my_watchlist", None)

        if "my_watchlist" not in st.session_state:
            with st.spinner("Loading your watchlist…"):
                try:
                    st.session_state["my_watchlist"] = fetch_my_watchlist()
                except ApiError as error:
                    st.session_state["my_watchlist"] = []
                    st.error(str(error))

        watching = st.session_state.get("my_watchlist", [])
        if not watching:
            empty_state("Nothing on your watchlist yet.")
        else:
            for entry in watching:
                target = entry.get("target_price")
                target_line = f"Target {target:,.2f}" if target is not None else "No target price"
                st.markdown(
                    f'<div class="bw-card"><div class="bw-row">'
                    f'<span class="bw-seller">Variant #{entry["variant_id"]}</span>'
                    f'<span class="bw-badge bw-badge-best">#{entry["watchlist_id"]}</span></div>'
                    f'<div class="bw-meta" style="margin-top:0.45rem">{html.escape(target_line)}</div>'
                    f'<div class="bw-meta">Created {html.escape(pretty_timestamp(entry.get("created_at")))}</div>'
                    f"</div>",
                    unsafe_allow_html=True,
                )


def render_policy_chunk(chunk: dict[str, Any]) -> None:
    metadata = chunk.get("metadata") or {}
    policy_type = str(metadata.get("policy_type", "policy")).replace("_", " ").title()
    category = metadata.get("category")

    tags = f'<span class="bw-badge bw-badge-best">{html.escape(policy_type)}</span>'
    if category:
        tags += f' <span class="bw-badge bw-badge-neutral">{html.escape(str(category))}</span>'

    st.markdown(
        f'<div class="bw-card"><div class="bw-row">'
        f'<span class="bw-seller">Seller #{html.escape(str(metadata.get("seller_id", "?")))}</span>{tags}</div>'
        f'<div class="bw-chunk-text">{html.escape(chunk.get("text", ""))}</div>'
        f'<div class="bw-meta" style="margin-top:0.6rem">Policy #{html.escape(str(metadata.get("policy_id", "?")))} '
        f'· chunk {html.escape(str(metadata.get("chunk_index", "?")))}</div></div>',
        unsafe_allow_html=True,
    )


def page_policies() -> None:
    hero(
        "Seller policies",
        "Semantic policy search",
        "Questions go through the embedding index, so wording does not have to match the policy text.",
    )

    with st.form("policy_search_form"):
        query = st.text_input("Question", placeholder="How many days do I get to return a damaged item?")
        filter_col, count_col, submit_col = st.columns([1.2, 1.2, 1], vertical_alignment="bottom")
        seller_id = filter_col.number_input(
            "Seller ID",
            min_value=1,
            step=1,
            value=None,
            help="Optional — leave blank to search every seller.",
        )
        n_results = count_col.slider("Results", min_value=1, max_value=10, value=3)
        submitted = submit_col.form_submit_button("Search", type="primary", use_container_width=True)

    if submitted:
        if not query.strip():
            st.warning("Type a question before searching.")
        else:
            with st.spinner("Embedding the question and searching the policy index…"):
                try:
                    st.session_state["policy_chunks"] = search_seller_policies(
                        query.strip(),
                        int(n_results),
                        int(seller_id) if seller_id is not None else None,
                    )
                except ApiError as error:
                    st.session_state.pop("policy_chunks", None)
                    st.error(str(error))

    chunks = st.session_state.get("policy_chunks")
    if chunks is not None:
        if not chunks:
            empty_state("Nothing in the policy index matched that question.")
        else:
            st.caption(f"{len(chunks)} matching passage(s)")
            for chunk in chunks:
                render_policy_chunk(chunk)

    with st.expander("Add a policy to the index"):
        with st.form("policy_create_form"):
            id_col, type_col, cat_col = st.columns(3)
            new_seller_id = id_col.number_input("Seller ID", min_value=1, step=1, value=1, key="new_policy_seller")
            policy_type = type_col.text_input("Policy type", value="return_policy")
            category = cat_col.text_input("Category", placeholder="optional")
            policy_text = st.text_area("Policy text", height=130)
            source_url = st.text_input("Source URL", placeholder="optional")
            created = st.form_submit_button("Save and embed", type="primary")

        if created:
            if not policy_text.strip() or not policy_type.strip():
                st.warning("Policy type and policy text are both required.")
            else:
                with st.spinner("Saving to Postgres and embedding into Chroma…"):
                    try:
                        policy = create_seller_policy(
                            int(new_seller_id),
                            policy_type.strip(),
                            category.strip() or None,
                            policy_text.strip(),
                            source_url.strip() or None,
                        )
                    except ApiError as error:
                        st.error(str(error))
                    else:
                        st.toast("Policy embedded", icon="📄")
                        st.success(f"Saved policy #{policy['policy_id']} for seller #{policy['seller_id']}.")


PAGES = {
    "Price search": page_price_search,
    "Ask the agent": page_agent,
    "Watchlist": page_watchlist,
    "Seller policies": page_policies,
}


def render_auth_section() -> None:
    if st.session_state.get("token"):
        st.markdown(f"**Signed in as** {html.escape(st.session_state['username'])}")
        if st.button("Log out", use_container_width=True):
            st.session_state["token"] = None
            st.session_state["username"] = None
            st.session_state.pop("my_watchlist", None)
            st.rerun()
        return

    login_tab, signup_tab = st.tabs(["Log in", "Sign up"])

    with login_tab:
        with st.form("login_form"):
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
            submitted = st.form_submit_button("Log in", type="primary", use_container_width=True)

        if submitted:
            if not username.strip() or not password:
                st.warning("Enter a username and password.")
            else:
                try:
                    token_response = login_user(username.strip(), password)
                except ApiError as error:
                    st.error(str(error))
                else:
                    st.session_state["token"] = token_response["access_token"]
                    st.session_state["username"] = username.strip()
                    st.rerun()

    with signup_tab:
        with st.form("signup_form"):
            new_username = st.text_input("Username", key="signup_username")
            new_password = st.text_input(
                "Password", type="password", key="signup_password", help="At least 8 characters."
            )
            created = st.form_submit_button("Create account", type="primary", use_container_width=True)

        if created:
            if not new_username.strip() or not new_password:
                st.warning("Enter a username and password.")
            else:
                try:
                    signup_user(new_username.strip(), new_password)
                except ApiError as error:
                    st.error(str(error))
                else:
                    st.success("Account created — log in above.")


def render_sidebar() -> str:
    with st.sidebar:
        st.markdown("### 🛒 BuyWise AI")
        st.caption("Autonomous shopping & price intelligence")
        st.divider()

        render_auth_section()
        st.divider()

        choice = st.radio("Section", list(PAGES), label_visibility="collapsed")

        st.divider()
        online = backend_is_reachable(API_BASE_URL)
        colour, label = ("#22C55E", "Backend online") if online else ("#FB7185", "Backend unreachable")
        st.markdown(
            f'<div class="bw-status"><span class="bw-dot" style="background:{colour}"></span>{label}</div>'
            f'<div class="bw-status" style="margin-top:0.35rem">{html.escape(API_BASE_URL)}</div>',
            unsafe_allow_html=True,
        )
        if st.button("Recheck", use_container_width=True):
            backend_is_reachable.clear()
            st.rerun()
        st.caption("Point elsewhere with the `API_BASE_URL` env var.")

    return choice


def main() -> None:
    st.set_page_config(page_title="BuyWise AI", page_icon="🛒", layout="wide", initial_sidebar_state="expanded")
    st.session_state.setdefault("token", None)
    st.session_state.setdefault("username", None)
    st.markdown(CSS, unsafe_allow_html=True)
    PAGES[render_sidebar()]()


if __name__ == "__main__":
    main()

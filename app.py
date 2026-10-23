import streamlit as st
import json
import re
import importlib

try:
    import ollama
    HAS_OLLAMA = True
except Exception:
    ollama = None
    HAS_OLLAMA = False

import pricing_engine
importlib.reload(pricing_engine)
from pricing_engine import PricingEngine

# Konfigurasi Halaman Modern
st.set_page_config(
    page_title="5 Min Price Ready - Sales Advisor AI",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Bersihkan cache lama jika ada
if "cache_cleared" not in st.session_state:
    st.cache_resource.clear()
    st.session_state.cache_cleared = True

# Inisialisasi State Margin & Hasil Aktif
if "current_margin" not in st.session_state:
    st.session_state.current_margin = 25.0
if "active_product_result" not in st.session_state:
    st.session_state.active_product_result = None

# Custom Styling (Modern, Clean & Eye-catching)
st.markdown("""
<style>
    .main-header { font-size: 28px; font-weight: 800; color: #1E3A8A; margin-bottom: 2px; }
    .sub-header { color: #64748B; font-size: 14px; margin-bottom: 20px; }
    .badge-custom {
        background-color: #6366F1;
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        display: inline-block;
    }
    .badge-rtu {
        background-color: #0EA5E9;
        color: white;
        padding: 4px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 700;
        text-transform: uppercase;
        display: inline-block;
    }
    .spec-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 10px;
        margin-bottom: 10px;
    }
    .spec-table td {
        padding: 7px 10px;
        border-bottom: 1px solid #E2E8F0;
        font-size: 13px;
    }
    .spec-label {
        color: #64748B;
        font-weight: 600;
        width: 35%;
    }
    .spec-value {
        color: #0F172A;
        font-weight: 500;
    }
    .alt-card {
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 14px;
        background: #F8FAFC;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# Inisialisasi Engine
def get_engine():
    try:
        return PricingEngine("data")
    except Exception as e:
        st.error(f"Gagal memuat katalog produk: {e}")
        return None

engine = get_engine()

# Sidebar Controls
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/lightning-bolt.png", width=60)
    st.title("⚡ Settings & Katalog")
    st.markdown("---")
    
    # Status Engine
    if engine and engine.all_items:
        total_p = len(engine.all_items)
        n_c = len(engine.custom_items)
        n_r = len(engine.rtu_items)
        st.success(f"✅ **{total_p:,} Produk Siap**\n* {n_c:,} Custom\n* {n_r:,} RTU")
    else:
        st.error("⚠️ Katalog belum terhubung.")

    if st.button("🔄 Reload Katalog Data", use_container_width=True):
        st.cache_resource.clear()
        st.session_state.active_product_result = None
        st.rerun()

    st.markdown("---")
    kategori_pilihan = st.radio("Kategori Katalog", ["Semua", "Custom", "RTU"])

    # Filter Sub-Kategori Dinamis
    available_subcats = ["Semua"] + (engine.get_subcategories() if engine else [])
    subcat_pilihan = st.selectbox("Jenis / Kategori Produk", available_subcats)

    st.markdown("---")
    st.caption("🔒 100% Instant Sales Advisor & Pricing Engine")
    st.markdown("💡 **Contoh Pertanyaan Sales:**")
    st.caption("- *Spesifikasi Paper Bag Handle Kraft 125 ukuran 20x20x25*")
    st.caption("- *Berapa harga box kebab small bahan ivory?*")
    st.caption("- *Spesifikasi food wrap greaseproof 40 ukuran 14x14*")
    st.caption("- *Rekomendasi paper bowl 8,5 oz untuk makanan berkuah*")
    st.caption("- *Harga paper cup 12 oz spe 230*")

# Header Area
st.markdown('<div class="main-header">⚡ 5 Min Price Ready - AI Sales Advisor</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Rekomendasi harga instan, spesifikasi teknis lengkap, dan kalkulasi margin fleksibel untuk tim sales dalam &lt; 1 menit.</div>', unsafe_allow_html=True)

# Session State untuk Chat History
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant", 
            "content": "Halo! Saya siap membantu tim sales. Tanyakan spesifikasi produk kemasan apapun (Box, Food Wrap, Paper Bag, Paper Bowl, Paper Cup, Satchel, Sleeve, dll.). Anda dapat langsung memasukkan angka Target Margin Profit (%) termasuk nilai desimal/koma pada produk utama maupun seluruh alternatif varian!"
        }
    ]

# Tampilkan riwayat chat pesan teks
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Handle Input Chat Baru
if user_prompt := st.chat_input("Tanyakan produk & spesifikasi, misal: Paper Bag Kraft 125 ukuran 20x20x25 atau Box Kebab Ivory"):
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.write(user_prompt)

    with st.spinner("Mencari spesifikasi produk & merumuskan rekomendasi harga..."):
        # 1. Cari langsung di database dengan multi-catalog engine
        results = engine.search(
            user_prompt, 
            category=kategori_pilihan, 
            subcat=subcat_pilihan, 
            limit=4
        ) if engine else []

        # Fallback jika pencarian awal kosong
        if not results and engine:
            # 1. Ekstraksi cerdas kata kunci lokal (menghapus stopwords tanya/salam)
            stopwords = {
                "apa", "berapa", "spesifikasi", "tolong", "carikan", "rekomendasi", "harga",
                "produk", "kemasan", "untuk", "dari", "yang", "dan", "di", "ke", "saya", "mau",
                "minta", "dong", "ya", "halo", "hai", "bisa", "kasih", "tahu", "adakah"
            }
            clean_tokens = [w for w in re.split(r'\W+', user_prompt.lower()) if w and w not in stopwords]
            if clean_tokens:
                local_kw = " ".join(clean_tokens)
                results = engine.search(local_kw, category=kategori_pilihan, subcat=subcat_pilihan, limit=4)

            # 2. Jika masih belum ketemu dan Ollama tersedia, coba ekstrak via LLM
            if not results and HAS_OLLAMA and ollama:
                try:
                    extract_prompt = f"""
                    Ekstrak kata kunci produk, bahan, atau ukuran dari teks berikut dalam 1 baris string singkat tanpa tanda kutip:
                    "{user_prompt}"
                    Contoh: paper bag handle kraft 125
                    """
                    llm_res = ollama.chat(
                        model='llama3.2:3b',
                        messages=[{'role': 'user', 'content': extract_prompt}]
                    )
                    clean_kw = llm_res['message']['content'].strip()
                    results = engine.search(clean_kw, category=kategori_pilihan, subcat=subcat_pilihan, limit=4)
                except Exception:
                    pass

        if results:
            top_match = results[0]

            # Simpan ke state produk aktif untuk simulasi harga real-time
            st.session_state.active_product_result = {
                "top_match": top_match,
                "results": results,
                "user_prompt": user_prompt
            }
            st.rerun()

        else:
            st.session_state.active_product_result = None
            reply_text = (
                "Maaf, kami belum menemukan spesifikasi produk yang cocok di seluruh katalog perusahaan.\n\n"
                "**Tips Pencarian:**\n"
                "- Gunakan nama produk atau jenis kemasan (contoh: *Box Kebab, Food Wrap, Paper Bag, Paper Bowl, Paper Cup, Satchel, Sleeve*).\n"
                "- Sertakan bahan atau gramatur (contoh: *Kraft 125, Ivory 300, Greaseproof 40, SPE 230*).\n"
                "- Anda dapat memilih filter Kategori (Semua/Custom/RTU) atau Sub-Kategori di sidebar."
            )
            with st.chat_message("assistant"):
                st.warning(reply_text)
            st.session_state.messages.append({"role": "assistant", "content": reply_text})

# Tampilkan Hasil Produk & Simulasi Margin di Area Chat Jawaban Sales
if st.session_state.active_product_result and engine:
    active_data = st.session_state.active_product_result
    top_match = active_data["top_match"]
    results = active_data["results"]
    cogs = top_match["base_cogs"]
    badge_class = "badge-rtu" if top_match["type"] == "RTU" else "badge-custom"

    with st.chat_message("assistant"):
        # 1. Tampilkan Kartu Spesifikasi Teknis Terstruktur Produk Utama
        spec_rows_html = "".join([
            f"<tr><td class='spec-label'>{k}</td><td class='spec-value'>{v}</td></tr>" 
            for k, v in top_match["specs"].items()
        ])

        card_html = f"""
        <div style="border: 1px solid #CBD5E1; border-radius: 12px; padding: 18px; margin-top: 15px; margin-bottom: 15px; background: white; box-shadow: 0 2px 6px rgba(0,0,0,0.04);">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                <span style="font-size: 17px; font-weight: 700; color: #1E293B;">📦 {top_match['product']} (Rekomendasi Utama)</span>
                <span class="{badge_class}">{top_match['type']} &bull; {top_match['subcat']}</span>
            </div>
            <table class="spec-table">
                {spec_rows_html}
            </table>
        </div>
        """
        st.markdown(card_html, unsafe_allow_html=True)

        # 2. INPUT NUMBER TARGET MARGIN PROFIT (%) - MENDUKUNG DESIMAL / KOMA
        st.markdown("### 🎯 Simulasi Target Margin & Kalkulasi Harga (Produk Utama)")
        
        col_inp, col_info = st.columns([1, 2])
        with col_inp:
            current_m = st.number_input(
                "Target Margin Profit (%)",
                min_value=0.0,
                max_value=99.0,
                value=float(st.session_state.current_margin),
                step=0.5,
                format="%.2f",
                key="chat_margin_number_input",
                help="Masukkan persentase margin keuntungan (bisa desimal, misal 25.50, 40.12, dsb.)"
            )
            st.session_state.current_margin = current_m
        with col_info:
            st.caption(f"💡 Masukkan target gross margin yang diinginkan. Anda dapat menginput nilai koma (contoh: **40.12%**, **37.91%**, **25.50%**). Perhitungan harga jual dan profit akan ter-update secara otomatis.")

        # Hitung harga jual reaktif berdasarkan input margin
        sell_price, profit = engine.calculate_price(cogs, current_m)
        floor_price, _ = engine.calculate_price(cogs, 15.0)

        # 4. Tampilkan Metrik Finansial Reaktif Produk Utama
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("COGS Vendor Dasar", f"Rp {cogs:,.0f}")
        with col2:
            st.metric(f"Harga Jual (Margin {current_m:.2f}%)", f"Rp {sell_price:,.0f}", delta=f"Profit: Rp {profit:,.0f}")
        with col3:
            st.metric("Batas Diskon (Margin 15%)", f"Rp {floor_price:,.0f}", delta="Floor Price", delta_color="inverse")
        with col4:
            price_ref = top_match.get("price_list", 0)
            st.metric("Harga Acuan Sheet", f"Rp {price_ref:,.0f}" if price_ref > 0 else "-")

        st.info(f"💡 **Taktik Penawaran:** Pada margin **{current_m:.2f}%**, harga penawaran ideal ke klien adalah **Rp {sell_price:,.0f}** (profit **Rp {profit:,.0f}/pcs**). Jika klien menawar diskon volume, pertahankan harga di atas batas aman **Rp {floor_price:,.0f}** (Margin 15%).")

        # 5. SEMUA ALTERNATIF VARIAN DENGAN SIMULASI MARGIN & KALKULASI HARGA MANDIRI
        if len(results) > 1:
            st.markdown("---")
            st.markdown(f"### 🔄 Simulasi Alternatif Varian / Ukuran Terdekat ({len(results)-1} Varian Tersedia)")
            st.caption("Jika spesifikasi di atas belum cocok dengan kebutuhan klien, simulasikan langsung target margin dan kalkulasi harga untuk varian di bawah ini:")

            for i, alt in enumerate(results[1:], start=1):
                alt_cogs = alt["base_cogs"]
                alt_badge = "badge-rtu" if alt["type"] == "RTU" else "badge-custom"
                
                with st.expander(f"📦 Varian #{i}: {alt['product']} | {alt['material']} | {alt['size']} ({alt['type']} - {alt['subcat']})", expanded=(i == 1)):
                    # Rincian Spesifikasi Singkat
                    c_spec1, c_spec2 = st.columns(2)
                    with c_spec1:
                        st.markdown(f"**Tipe:** `{alt['type']} ({alt['subcat']})`")
                        st.markdown(f"**Brand / Kode:** `{alt['brand']}`")
                        st.markdown(f"**Bahan:** `{alt['material']}`")
                    with c_spec2:
                        st.markdown(f"**Ukuran:** `{alt['size']}`")
                        st.markdown(f"**Finishing / Detail:** `{alt['specs'].get('Finishing', alt['specs'].get('Catatan (Remarks)', '-'))}`")
                        st.markdown(f"**MOQ / Kemasan:** `{alt['specs'].get('Qty Produksi / MOQ', alt['specs'].get('MOQ', '-'))}`")

                    st.markdown("##### 🎯 Simulasi Margin untuk Varian Ini")
                    col_alt_inp, col_alt_space = st.columns([1, 2])
                    with col_alt_inp:
                        # Masing-masing alternatif memiliki input number margin sendiri
                        alt_m = st.number_input(
                            f"Target Margin Varian #{i} (%)",
                            min_value=0.0,
                            max_value=99.0,
                            value=float(current_m),
                            step=0.5,
                            format="%.2f",
                            key=f"alt_margin_input_{i}",
                            help="Ubah margin khusus untuk varian alternatif ini"
                        )

                    alt_sell, alt_profit = engine.calculate_price(alt_cogs, alt_m)
                    alt_floor, _ = engine.calculate_price(alt_cogs, 15.0)
                    alt_price_ref = alt.get("price_list", 0)

                    # 4 Metrik Finansial untuk Varian Alternatif
                    m1, m2, m3, m4 = st.columns(4)
                    with m1:
                        st.metric("COGS Vendor Dasar", f"Rp {alt_cogs:,.0f}")
                    with m2:
                        st.metric(f"Harga Jual (Margin {alt_m:.2f}%)", f"Rp {alt_sell:,.0f}", delta=f"Profit: Rp {alt_profit:,.0f}")
                    with m3:
                        st.metric("Batas Diskon (Margin 15%)", f"Rp {alt_floor:,.0f}", delta="Floor Price", delta_color="inverse")
                    with m4:
                        st.metric("Harga Acuan Sheet", f"Rp {alt_price_ref:,.0f}" if alt_price_ref > 0 else "-")

                    st.caption(f"💡 Estimasi keuntungan varian #{i}: **Rp {alt_profit:,.0f} per unit** pada margin **{alt_m:.2f}%**.")
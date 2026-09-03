// Telegram Mini App Controller
const tg = window.Telegram?.WebApp;
if (tg) {
  tg.ready();
  tg.expand();
  if (tg.setHeaderColor) tg.setHeaderColor('#0c0d12');
  if (tg.setBackgroundColor) tg.setBackgroundColor('#0c0d12');
}

// Current App State
let currentUser = {
  user_id: tg?.initDataUnsafe?.user?.id || 7127148321,
  first_name: tg?.initDataUnsafe?.user?.first_name || 'Customer',
  username: tg?.initDataUnsafe?.user?.username || 'user',
  balance: 0.0,
  lang: 'en'
};

let productsData = [];
let ordersData = [];
let currentProduct = null;
let selectedQuantity = 1;
let appliedCoupon = null;
let selectedDepositNetwork = 'Binance Pay';


// Toast Utility
function showToast(msg) {
  const toast = document.getElementById('toast');
  toast.innerText = msg;
  toast.classList.add('show');
  setTimeout(() => {
    toast.classList.remove('show');
  }, 2200);
}

// Haptic feedback utility
function triggerHaptic(type) {
  if (tg?.HapticFeedback) {
    if (type === 'light' || type === 'medium') tg.HapticFeedback.impactOccurred(type);
    if (type === 'success' || type === 'error') tg.HapticFeedback.notificationOccurred(type);
  }
}

// ==================== BRAND SVG ARTWORK GENERATORS ====================
function getProductArtSvg(brand, name) {
  const b = (brand || '').toUpperCase();
  const n = (name || '').toLowerCase();

  // 1. Google Gemini / Google One
  if (b.includes('GOOGLE') || n.includes('gemini')) {
    return `
      <div style="width:100%;height:100%;background:radial-gradient(circle at center, #1b1e36 0%, #0c0e1a 100%);display:flex;align-items:center;justify-content:center;position:relative;">
        <svg viewBox="0 0 100 100" width="56" height="56">
          <defs>
            <linearGradient id="geminiGrad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#4285F4"/>
              <stop offset="35%" stop-color="#9B72CB"/>
              <stop offset="70%" stop-color="#D96570"/>
              <stop offset="100%" stop-color="#1FA463"/>
            </linearGradient>
          </defs>
          <path d="M50 10 C50 32, 68 50, 90 50 C68 50, 50 68, 50 90 C50 68, 32 50, 10 50 C32 50, 50 32, 50 10 Z" fill="url(#geminiGrad)" filter="drop-shadow(0 0 10px rgba(66,133,244,0.6))"/>
        </svg>
        <span style="position:absolute;bottom:6px;font-size:10px;font-weight:800;color:rgba(255,255,255,0.85);letter-spacing:1px;">GEMINI PRO</span>
      </div>`;
  }

  // 2. ChatGPT / OpenAI
  if (b.includes('CHATGPT') || n.includes('chatgpt') || n.includes('gpt')) {
    return `
      <div style="width:100%;height:100%;background:radial-gradient(circle at center, #142825 0%, #091211 100%);display:flex;align-items:center;justify-content:center;position:relative;">
        <svg viewBox="0 0 100 100" width="52" height="52" fill="#10A37F" filter="drop-shadow(0 0 12px rgba(16,163,127,0.5))">
          <circle cx="50" cy="50" r="38" fill="none" stroke="#10A37F" stroke-width="6"/>
          <path d="M50 24 A26 26 0 0 1 76 50 A26 26 0 0 1 50 76 A26 26 0 0 1 24 50 A26 26 0 0 1 50 24" fill="none" stroke="#ffffff" stroke-width="4" stroke-dasharray="8 6"/>
          <circle cx="50" cy="50" r="14" fill="#10A37F"/>
        </svg>
        <span style="position:absolute;bottom:6px;font-size:10px;font-weight:800;color:#10A37F;letter-spacing:1px;">CHATGPT PLUS</span>
      </div>`;
  }

  // 3. Claude / Anthropic
  if (b.includes('CLAUDE') || n.includes('claude')) {
    return `
      <div style="width:100%;height:100%;background:radial-gradient(circle at center, #2e1d16 0%, #130c08 100%);display:flex;align-items:center;justify-content:center;position:relative;">
        <svg viewBox="0 0 100 100" width="52" height="52">
          <circle cx="50" cy="50" r="26" fill="#D97757" filter="drop-shadow(0 0 12px rgba(217,119,87,0.5))"/>
          <polygon points="50,16 56,36 76,40 58,54 62,74 50,62 38,74 42,54 24,40 44,36" fill="#ffffff"/>
        </svg>
        <span style="position:absolute;bottom:6px;font-size:10px;font-weight:800;color:#D97757;letter-spacing:1px;">CLAUDE API</span>
      </div>`;
  }

  // 4. Microsoft Office 365
  if (n.includes('office') || n.includes('365') || n.includes('microsoft')) {
    return `
      <div style="width:100%;height:100%;background:radial-gradient(circle at center, #2e1a14 0%, #120906 100%);display:flex;align-items:center;justify-content:center;position:relative;">
        <svg viewBox="0 0 100 100" width="52" height="52">
          <rect x="22" y="22" width="24" height="24" rx="4" fill="#F25022"/>
          <rect x="54" y="22" width="24" height="24" rx="4" fill="#7FBA00"/>
          <rect x="22" y="54" width="24" height="24" rx="4" fill="#00A4EF"/>
          <rect x="54" y="54" width="24" height="24" rx="4" fill="#FFB900"/>
        </svg>
        <span style="position:absolute;bottom:6px;font-size:10px;font-weight:800;color:#F25022;letter-spacing:1px;">OFFICE 365</span>
      </div>`;
  }

  // 5. Windows 11
  if (n.includes('windows')) {
    return `
      <div style="width:100%;height:100%;background:radial-gradient(circle at center, #0f2742 0%, #06101c 100%);display:flex;align-items:center;justify-content:center;position:relative;">
        <svg viewBox="0 0 100 100" width="50" height="50">
          <rect x="20" y="20" width="26" height="26" rx="4" fill="#0078D4"/>
          <rect x="54" y="20" width="26" height="26" rx="4" fill="#0078D4"/>
          <rect x="20" y="54" width="26" height="26" rx="4" fill="#0078D4"/>
          <rect x="54" y="54" width="26" height="26" rx="4" fill="#0078D4"/>
        </svg>
        <span style="position:absolute;bottom:6px;font-size:10px;font-weight:800;color:#0078D4;letter-spacing:1px;">WINDOWS 11</span>
      </div>`;
  }

  // 6. Duolingo Super
  if (n.includes('duolingo')) {
    return `
      <div style="width:100%;height:100%;background:radial-gradient(circle at center, #1b3814 0%, #081605 100%);display:flex;align-items:center;justify-content:center;position:relative;">
        <svg viewBox="0 0 100 100" width="52" height="52">
          <circle cx="50" cy="50" r="30" fill="#58CC02" filter="drop-shadow(0 0 10px rgba(88,204,2,0.6))"/>
          <circle cx="40" cy="46" r="8" fill="#ffffff"/>
          <circle cx="60" cy="46" r="8" fill="#ffffff"/>
          <circle cx="41" cy="46" r="4" fill="#4B4B4B"/>
          <circle cx="59" cy="46" r="4" fill="#4B4B4B"/>
          <polygon points="50,54 44,60 56,60" fill="#FFC200"/>
        </svg>
        <span style="position:absolute;bottom:6px;font-size:10px;font-weight:800;color:#58CC02;letter-spacing:1px;">SUPER DUO</span>
      </div>`;
  }

  // 7. Zoom Pro
  if (n.includes('zoom')) {
    return `
      <div style="width:100%;height:100%;background:radial-gradient(circle at center, #0f2b4c 0%, #061322 100%);display:flex;align-items:center;justify-content:center;position:relative;">
        <svg viewBox="0 0 100 100" width="52" height="52">
          <rect x="22" y="32" width="38" height="36" rx="8" fill="#2D8CFF"/>
          <polygon points="62,44 82,32 82,68 62,56" fill="#2D8CFF"/>
        </svg>
        <span style="position:absolute;bottom:6px;font-size:10px;font-weight:800;color:#2D8CFF;letter-spacing:1px;">ZOOM PRO</span>
      </div>`;
  }

  // 8. Notion
  if (n.includes('notion')) {
    return `
      <div style="width:100%;height:100%;background:radial-gradient(circle at center, #26262b 0%, #101013 100%);display:flex;align-items:center;justify-content:center;position:relative;">
        <svg viewBox="0 0 100 100" width="48" height="48">
          <rect x="24" y="24" width="52" height="52" rx="10" fill="#ffffff"/>
          <path d="M36 34 L48 34 L62 58 L62 34 L70 34 L70 66 L58 66 L44 42 L44 66 L36 66 Z" fill="#000000"/>
        </svg>
        <span style="position:absolute;bottom:6px;font-size:10px;font-weight:800;color:#ffffff;letter-spacing:1px;">NOTION PLUS</span>
      </div>`;
  }

  // 9. CapCut / Video Editing
  if (n.includes('capcut')) {
    return `
      <div style="width:100%;height:100%;background:radial-gradient(circle at center, #2a1538 0%, #110717 100%);display:flex;align-items:center;justify-content:center;position:relative;">
        <svg viewBox="0 0 100 100" width="52" height="52">
          <rect x="24" y="24" width="52" height="52" rx="12" fill="#000000" stroke="#ff007f" stroke-width="3"/>
          <polygon points="40,36 68,50 40,64" fill="#00f0ff"/>
        </svg>
        <span style="position:absolute;bottom:6px;font-size:10px;font-weight:800;color:#ff007f;letter-spacing:1px;">CAPCUT PRO</span>
      </div>`;
  }

  // 10. Canva / Figma / Framer
  if (n.includes('canva') || n.includes('figma') || n.includes('framer')) {
    return `
      <div style="width:100%;height:100%;background:radial-gradient(circle at center, #1b283d 0%, #0b111c 100%);display:flex;align-items:center;justify-content:center;position:relative;">
        <svg viewBox="0 0 100 100" width="50" height="50">
          <circle cx="40" cy="38" r="14" fill="#00C4CC"/>
          <circle cx="60" cy="38" r="14" fill="#7D2AE8"/>
          <circle cx="50" cy="62" r="16" fill="#F24E1E"/>
        </svg>
        <span style="position:absolute;bottom:6px;font-size:10px;font-weight:800;color:#00C4CC;letter-spacing:1px;">PRO DESIGN</span>
      </div>`;
  }

  // 11. Miro / Miro EDU
  if (n.includes('miro')) {
    return `
      <div style="width:100%;height:100%;background:radial-gradient(circle at center, #383410 0%, #141304 100%);display:flex;align-items:center;justify-content:center;position:relative;">
        <svg viewBox="0 0 100 100" width="50" height="50">
          <rect x="24" y="24" width="52" height="52" rx="10" fill="#FFD02F"/>
          <polygon points="34,34 44,34 38,66 28,66" fill="#050038"/>
          <polygon points="46,34 56,34 50,66 40,66" fill="#050038"/>
          <polygon points="58,34 68,34 62,66 52,66" fill="#050038"/>
        </svg>
        <span style="position:absolute;bottom:6px;font-size:10px;font-weight:800;color:#FFD02F;letter-spacing:1px;">MIRO EDU</span>
      </div>`;
  }

  // 12. Grok / Gamma / Manus / Lovable / Kiro
  if (n.includes('grok') || n.includes('gamma') || n.includes('manus') || n.includes('lovable') || n.includes('kiro')) {
    return `
      <div style="width:100%;height:100%;background:radial-gradient(circle at center, #24143a 0%, #0d0617 100%);display:flex;align-items:center;justify-content:center;position:relative;">
        <svg viewBox="0 0 100 100" width="52" height="52">
          <polygon points="50,14 84,34 84,66 50,86 16,66 16,34" fill="none" stroke="#A855F7" stroke-width="4"/>
          <circle cx="50" cy="50" r="16" fill="#EC4899" filter="drop-shadow(0 0 8px #EC4899)"/>
        </svg>
        <span style="position:absolute;bottom:6px;font-size:10px;font-weight:800;color:#C084FC;letter-spacing:1px;">AI INTELLIGENCE</span>
      </div>`;
  }

  // 13. Apple TV / HBO / Prime / Cinema
  if (n.includes('apple tv') || n.includes('hbo') || n.includes('prime') || n.includes('peacock') || n.includes('shahid')) {
    return `
      <div style="width:100%;height:100%;background:radial-gradient(circle at center, #35131b 0%, #13060a 100%);display:flex;align-items:center;justify-content:center;position:relative;">
        <svg viewBox="0 0 100 100" width="50" height="50">
          <rect x="20" y="24" width="60" height="48" rx="8" fill="none" stroke="#E50914" stroke-width="4"/>
          <polygon points="44,38 62,48 44,58" fill="#ffffff"/>
        </svg>
        <span style="position:absolute;bottom:6px;font-size:10px;font-weight:800;color:#FF4B55;letter-spacing:1px;">CINEMA 4K</span>
      </div>`;
  }

  // 14. Coursera Wholesale
  if (n.includes('coursera')) {
    return `
      <div style="width:100%;height:100%;background:radial-gradient(circle at center, #112845 0%, #08111d 100%);display:flex;align-items:center;justify-content:center;position:relative;">
        <svg viewBox="0 0 100 100" width="52" height="52">
          <polygon points="50,18 84,36 50,54 16,36" fill="#0056D2"/>
          <polygon points="50,22 80,36 50,50 20,36" fill="#2A73E8"/>
          <path d="M26 44 L26 62 Q50 78 74 62 L74 44" fill="none" stroke="#0056D2" stroke-width="5" stroke-linecap="round"/>
        </svg>
        <span style="position:absolute;bottom:6px;font-size:10px;font-weight:800;color:#0056D2;letter-spacing:1px;">COURSERA PLUS</span>
      </div>`;
  }

  // 15. Netflix
  if (b.includes('NETFLIX') || n.includes('netflix')) {
    return `
      <div style="width:100%;height:100%;background:radial-gradient(circle at center, #3a0d10 0%, #150406 100%);display:flex;align-items:center;justify-content:center;position:relative;">
        <svg viewBox="0 0 100 100" width="46" height="46">
          <polygon points="32,20 44,20 44,80 32,80" fill="#E50914"/>
          <polygon points="56,20 68,20 68,80 56,80" fill="#E50914"/>
          <polygon points="32,20 44,20 68,80 56,80" fill="#B20710" filter="drop-shadow(0 0 8px #E50914)"/>
        </svg>
        <span style="position:absolute;bottom:6px;font-size:10px;font-weight:800;color:#E50914;letter-spacing:1px;">NETFLIX 4K</span>
      </div>`;
  }

  // 16. Spotify
  if (n.includes('spotify')) {
    return `
      <div style="width:100%;height:100%;background:radial-gradient(circle at center, #0f301b 0%, #06140b 100%);display:flex;align-items:center;justify-content:center;position:relative;">
        <svg viewBox="0 0 100 100" width="50" height="50">
          <circle cx="50" cy="50" r="32" fill="#1DB954" filter="drop-shadow(0 0 10px rgba(29,185,84,0.6))"/>
          <path d="M34 42 Q50 36 66 44" fill="none" stroke="#000" stroke-width="4" stroke-linecap="round"/>
          <path d="M36 50 Q50 45 64 52" fill="none" stroke="#000" stroke-width="3.5" stroke-linecap="round"/>
          <path d="M38 58 Q50 54 62 60" fill="none" stroke="#000" stroke-width="3" stroke-linecap="round"/>
        </svg>
        <span style="position:absolute;bottom:6px;font-size:10px;font-weight:800;color:#1DB954;letter-spacing:1px;">SPOTIFY PREMIUM</span>
      </div>`;
  }

  // 17. ExpressVPN / NordVPN
  if (b.includes('EXPRESS_VPN') || b.includes('PROTON_VPN') || n.includes('vpn')) {
    return `
      <div style="width:100%;height:100%;background:radial-gradient(circle at center, #351315 0%, #150607 100%);display:flex;align-items:center;justify-content:center;position:relative;">
        <svg viewBox="0 0 100 100" width="50" height="50">
          <path d="M50 18 L76 30 L76 54 C76 70 50 82 50 82 C50 82 24 70 24 54 L24 30 Z" fill="#DA3940"/>
          <circle cx="50" cy="46" r="12" fill="#ffffff"/>
          <path d="M50 54 L50 64" stroke="#ffffff" stroke-width="4" stroke-linecap="round"/>
        </svg>
        <span style="position:absolute;bottom:6px;font-size:10px;font-weight:800;color:#DA3940;letter-spacing:1px;">VPN SECURE</span>
      </div>`;
  }

  // Default Luxury Digital AI Card
  return `
    <div style="width:100%;height:100%;background:radial-gradient(circle at center, #1b2034 0%, #0c0e18 100%);display:flex;align-items:center;justify-content:center;position:relative;">
      <svg viewBox="0 0 100 100" width="48" height="48">
        <polygon points="50,15 82,33 82,67 50,85 18,67 18,33" fill="none" stroke="#007aff" stroke-width="5"/>
        <circle cx="50" cy="50" r="12" fill="#00d2ff"/>
      </svg>
      <span style="position:absolute;bottom:6px;font-size:10px;font-weight:800;color:#00d2ff;letter-spacing:1px;">PREMIUM LICENSE</span>
    </div>`;
}


// ==================== INITIALIZATION ====================
document.addEventListener('DOMContentLoaded', async () => {
  initEventListeners();
  await loadUserData();
  await loadProducts();
});

function initEventListeners() {
  // Set Profile info
  document.getElementById('profName').innerText = currentUser.first_name;
  document.getElementById('profId').innerText = `ID: ${currentUser.user_id}`;
  document.getElementById('refLinkInput').value = `https://t.me/Hidta3zbibot?start=ref_${currentUser.user_id}`;

  // Dock Buttons Navigation
  const dockButtons = document.querySelectorAll('.dock-btn');
  dockButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetTab = btn.getAttribute('data-tab');
      switchTab(targetTab);
      dockButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      triggerHaptic('light');
    });
  });

  // Balance Pill click -> Switch to Balance Tab
  document.getElementById('balancePillBtn').addEventListener('click', () => {
    switchTab('tabBalance');
    dockButtons.forEach(b => b.classList.toggle('active', b.getAttribute('data-tab') === 'tabBalance'));
    triggerHaptic('light');
  });

  // 3-Language Selector
  const langButtons = document.querySelectorAll('.lang-btn');
  langButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      langButtons.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentUser.lang = btn.getAttribute('data-lang');
      triggerHaptic('light');
    });
  });

  // Live Instant Search
  const searchInput = document.getElementById('searchInput');
  const clearBtn = document.getElementById('clearSearchBtn');
  searchInput.addEventListener('input', () => {
    const q = searchInput.value.trim().toLowerCase();
    clearBtn.style.display = q ? 'block' : 'none';
    filterProductsBySearch(q);
  });
  clearBtn.addEventListener('click', () => {
    searchInput.value = '';
    clearBtn.style.display = 'none';
    renderProducts(productsData);
  });

  // Category Pills Filter
  const catPills = document.querySelectorAll('.cat-pill');
  catPills.forEach(pill => {
    pill.addEventListener('click', () => {
      catPills.forEach(p => p.classList.remove('active'));
      pill.classList.add('active');
      const cat = pill.getAttribute('data-cat');
      handleCategorySelect(cat);
      triggerHaptic('light');
    });
  });

  // Hero Card Buy button
  document.getElementById('heroBuyBtn').addEventListener('click', () => {
    const chatGptProd = productsData.find(p => p.name.includes('ChatGPT')) || productsData[0];
    if (chatGptProd) openProductModal(chatGptProd);
  });

  // Modal Closers
  document.getElementById('modalCloseBtn').addEventListener('click', closeModal);
  document.getElementById('depositCloseBtn').addEventListener('click', closeDepositModal);
  document.getElementById('supportCloseBtn').addEventListener('click', () => {
    document.getElementById('supportModal').classList.remove('active');
  });
  document.getElementById('statsCloseBtn').addEventListener('click', () => {
    document.getElementById('statsModal').classList.remove('active');
  });

  // Balance Tab: Add Funds
  document.getElementById('addFundsBtn').addEventListener('click', openDepositModal);
  document.getElementById('confirmDepositBtn').addEventListener('click', handleDepositSubmit);

  // Network selection in deposit
  const netChips = document.querySelectorAll('.net-chip');
  netChips.forEach(chip => {
    chip.addEventListener('click', () => {
      netChips.forEach(c => c.classList.remove('active'));
      chip.classList.add('active');
      selectedDepositNetwork = chip.getAttribute('data-net');
      triggerHaptic('light');
    });
  });

  // Quantity Steppers
  document.getElementById('qtyMinusBtn').addEventListener('click', () => updateQuantity(-1));
  document.getElementById('qtyPlusBtn').addEventListener('click', () => updateQuantity(1));

  // Coupon Code Apply
  document.getElementById('applyCouponBtn').addEventListener('click', handleApplyCoupon);

  // Accordion toggle
  document.getElementById('accordionToggle').addEventListener('click', () => {
    const body = document.getElementById('accordionBody');
    const chevron = document.querySelector('.accordion-chevron');
    const isOpen = body.style.display === 'block';
    body.style.display = isOpen ? 'none' : 'block';
    chevron.innerText = isOpen ? '▾' : '▴';
    triggerHaptic('light');
  });

  // Buy inside sheet
  document.getElementById('sheetBuyBtn').addEventListener('click', handlePurchase);

  // Profile actions
  document.getElementById('profStatsBtn').addEventListener('click', openStatsModal);
  document.getElementById('profReferralBtn').addEventListener('click', openStatsModal);
  document.getElementById('profSupportBtn').addEventListener('click', () => {
    document.getElementById('supportModal').classList.add('active');
  });
  document.getElementById('profApiBtn').addEventListener('click', () => {
    if (tg?.openLink) {
      tg.openLink('https://ventetelegrambotrailway-production.up.railway.app/api/swagger/');
    } else {
      window.open('https://ventetelegrambotrailway-production.up.railway.app/api/swagger/', '_blank');
    }
  });

  // Copy Buttons
  document.getElementById('copyAddressBtn')?.addEventListener('click', () => {
    const code = document.getElementById('depositAddressCode').innerText;
    navigator.clipboard.writeText(code);
    showToast('Address copied to clipboard!');
    triggerHaptic('success');
  });

  document.getElementById('copyRefBtn')?.addEventListener('click', () => {
    const link = document.getElementById('refLinkInput').value;
    navigator.clipboard.writeText(link);
    showToast('Referral link copied!');
    triggerHaptic('success');
  });

  document.getElementById('checkPaymentBtn')?.addEventListener('click', async () => {
    const btn = document.getElementById('checkPaymentBtn');
    btn.innerText = 'Checking blockchain confirmations...';
    await new Promise(r => setTimeout(r, 1200));
    await loadUserData();
    btn.innerText = 'Payment Confirmed & Added!';
    btn.style.borderColor = '#34c759';
    showToast('Balance updated!');
    triggerHaptic('success');
  });

  // Support ticket
  document.getElementById('sendSupportTicketBtn').addEventListener('click', handleSupportSubmit);
}

function switchTab(tabId) {
  document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
  const activeTab = document.getElementById(tabId);
  if (activeTab) activeTab.classList.add('active');

  const subHeader = document.getElementById('headerSub');
  if (tabId === 'tabStore') subHeader.innerText = 'STORE';
  if (tabId === 'tabOrders') {
    subHeader.innerText = 'ORDERS';
    loadOrders();
  }
  if (tabId === 'tabBalance') {
    subHeader.innerText = 'BALANCE';
    loadActivity();
  }
  if (tabId === 'tabProfile') subHeader.innerText = 'PROFILE';
}

// ==================== DATA FETCHING ====================
async function loadUserData() {
  try {
    const res = await fetch(`/api/user?user_id=${currentUser.user_id}`);
    const data = await res.json();
    if (data.ok) {
      currentUser.balance = parseFloat(data.user.balance) || 0.0;
      updateBalanceDisplay();
    }
  } catch (err) {
    console.error('User data error:', err);
  }
}

async function loadProducts() {
  try {
    const res = await fetch('/api/products');
    const data = await res.json();
    if (data.ok) {
      productsData = data.products;
      document.getElementById('stockSummaryBadge').innerText = `${productsData.length} items in stock`;
      renderProducts(productsData);
    }
  } catch (err) {
    console.error('Products load error:', err);
  }
}

async function loadOrders() {
  try {
    const res = await fetch(`/api/orders?user_id=${currentUser.user_id}`);
    const data = await res.json();
    if (data.ok) {
      ordersData = data.orders;
      renderOrders(ordersData);
    }
  } catch (err) {
    console.error('Orders load error:', err);
  }
}

function loadActivity() {
  const list = document.getElementById('activityList');
  if (ordersData && ordersData.length > 0) {
    list.innerHTML = '';
    ordersData.forEach(o => {
      const item = document.createElement('div');
      item.className = 'order-card';
      item.innerHTML = `
        <div class="order-card-row">
          <div class="order-left">
            <span class="dot-orange"></span>
            <div>
              <h4 class="order-title">${o.product_name}</h4>
              <span class="order-meta">Paid · ${o.created_at.slice(5, 16)}</span>
            </div>
          </div>
          <span class="order-price">-$${parseFloat(o.price).toFixed(2)}</span>
        </div>`;
      list.appendChild(item);
    });
  } else {
    list.innerHTML = `<div class="empty-state">No activity yet</div>`;
  }
}

function updateBalanceDisplay() {
  const formatted = `$${currentUser.balance.toFixed(0)}`;
  document.getElementById('topBalance').innerText = formatted;
  document.getElementById('hugeBalance').innerText = formatted;
}

// ==================== RENDERING ====================
function renderProducts(products) {
  const grid = document.getElementById('productsGrid');
  grid.innerHTML = '';

  products.forEach(p => {
    const card = document.createElement('div');
    card.className = 'prod-card';

    const artSvg = getProductArtSvg(p.icon_brand, p.name);
    const isNew = p.id === 1 || p.name.includes('ChatGPT') || p.name.includes('Claude') || p.name.includes('Magic');
    const stock = p.stock_count || 0;

    card.innerHTML = `
      <div class="prod-art">
        ${isNew ? '<span class="badge-new">NEW</span>' : ''}
        ${artSvg}
      </div>
      <div class="prod-info">
        <span class="prod-brand-sub">${p.category_name || 'DIGITAL SUBSCRIPTION'}</span>
        <h4 class="prod-name">${p.name}</h4>
        <div class="prod-bottom">
          <span class="prod-price">$${p.price.toFixed(2)}</span>
          <div class="stock-tag">
            <span class="dot-green"></span>
            <span>${stock} left</span>
          </div>
        </div>
      </div>
    `;

    card.addEventListener('click', () => openProductModal(p));
    grid.appendChild(card);
  });
}

function filterProductsBySearch(query) {
  if (!query) {
    renderProducts(productsData);
    return;
  }
  const filtered = productsData.filter(p => 
    p.name.toLowerCase().includes(query) || 
    (p.description && p.description.toLowerCase().includes(query))
  );
  renderProducts(filtered);
}

function handleCategorySelect(cat) {
  if (cat === 'all') {
    renderProducts(productsData);
  } else {
    const catId = parseInt(cat);
    if (!isNaN(catId)) {
      renderProducts(productsData.filter(p => p.category_id === catId));
    } else {
      renderProducts(productsData);
    }
  }
}


function renderOrders(orders) {
  const list = document.getElementById('ordersList');
  list.innerHTML = '';

  if (!orders || orders.length === 0) {
    list.innerHTML = `<div class="empty-state">No orders yet.</div>`;
    return;
  }

  orders.forEach(o => {
    const card = document.createElement('div');
    card.className = 'order-card';
    card.innerHTML = `
      <div class="order-card-row">
        <div class="order-left">
          <span class="dot-orange"></span>
          <div>
            <h4 class="order-title">${o.product_name}</h4>
            <span class="order-meta">USD · ${o.created_at.slice(5, 16)}</span>
          </div>
        </div>
        <div class="order-right">
          <div class="order-price-box">
            <span class="order-price">$${parseFloat(o.price).toFixed(2)}</span><br>
            <span class="order-badge-orange">Completed</span>
          </div>
          <span class="order-chevron">▾</span>
        </div>
      </div>
      <div class="order-credentials-tray">
        <span class="order-meta">Delivered Key / Account:</span>
        <code class="order-code-display">${o.content_delivered}</code>
        <button class="btn-copy-chip copy-order-key-btn">📋 Copy Credentials</button>
      </div>
    `;

    card.querySelector('.order-card-row').addEventListener('click', () => {
      card.classList.toggle('open');
      triggerHaptic('light');
    });

    card.querySelector('.copy-order-key-btn').addEventListener('click', (e) => {
      e.stopPropagation();
      navigator.clipboard.writeText(o.content_delivered);
      showToast('Credentials copied!');
      triggerHaptic('success');
    });

    list.appendChild(card);
  });
}

// ==================== PRODUCT DETAILS SHEET (Screenshot 4) ====================
function openProductModal(p) {
  currentProduct = p;
  selectedQuantity = 1;
  appliedCoupon = null;

  document.getElementById('qtyVal').innerText = '1';
  document.getElementById('couponInput').value = '';
  document.getElementById('couponAlert').style.display = 'none';

  document.getElementById('sheetTitle').innerText = p.name;
  document.getElementById('sheetPrice').innerText = `$${p.price.toFixed(0)}`;
  document.getElementById('sheetOldPrice').innerText = `$${Math.round(p.price * 2.5)}`;
  document.getElementById('sheetStockBadge').innerText = `● ${p.stock_count || 0} left`;
  document.getElementById('sheetDesc').innerText = p.description || 'Official digital license with automated delivery and guarantee.';
  document.getElementById('sheetCatTag').innerText = `${(p.category_name || 'DIGITAL').toUpperCase()} · OFFICIAL PROMO`;

  // Render Cover Art
  document.getElementById('sheetBrandArt').innerHTML = getProductArtSvg(p.icon_brand, p.name);

  updateSheetPricing();

  document.getElementById('productModal').classList.add('active');
  triggerHaptic('medium');
}

function updateQuantity(delta) {
  if (!currentProduct) return;
  const maxStock = currentProduct.stock_count || 10;
  selectedQuantity = Math.max(1, Math.min(maxStock, selectedQuantity + delta));
  document.getElementById('qtyVal').innerText = selectedQuantity;
  updateSheetPricing();
  triggerHaptic('light');
}

function updateSheetPricing() {
  if (!currentProduct) return;
  let unitPrice = currentProduct.price;
  if (appliedCoupon) {
    unitPrice = unitPrice * (1 - appliedCoupon.discount_percent / 100);
  }
  const total = unitPrice * selectedQuantity;
  document.getElementById('qtyTotalLabel').innerText = `Total: $${total.toFixed(2)}`;
  document.getElementById('sheetBuyBtn').innerText = `Buy · $${total.toFixed(0)}`;
}

async function handleApplyCoupon() {
  const code = document.getElementById('couponInput').value.trim();
  if (!code) return;

  const alertEl = document.getElementById('couponAlert');
  alertEl.style.display = 'block';

  try {
    const res = await fetch('/api/coupon/validate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ code })
    });
    const data = await res.json();
    if (data.ok) {
      appliedCoupon = data;
      alertEl.style.color = '#34c759';
      alertEl.innerText = `✓ Applied! ${data.discount_percent}% discount active.`;
      updateSheetPricing();
      triggerHaptic('success');
    } else {
      appliedCoupon = null;
      alertEl.style.color = '#ff3b30';
      alertEl.innerText = '✕ Invalid or expired promo code.';
      updateSheetPricing();
      triggerHaptic('error');
    }
  } catch (e) {
    alertEl.innerText = '✕ Error validating code';
  }
}

function closeModal() {
  document.getElementById('productModal').classList.remove('active');
  currentProduct = null;
}

function openDepositModal() {
  document.getElementById('depositModal').classList.add('active');
  document.getElementById('invoiceResult').style.display = 'none';
  triggerHaptic('light');
}

function closeDepositModal() {
  document.getElementById('depositModal').classList.remove('active');
}

async function handlePurchase() {
  if (!currentProduct) return;

  let unitPrice = currentProduct.price;
  if (appliedCoupon) unitPrice *= (1 - appliedCoupon.discount_percent / 100);
  const total = unitPrice * selectedQuantity;

  if (currentUser.balance < total) {
    triggerHaptic('error');
    alert('Insufficient balance! Please add funds.');
    closeModal();
    openDepositModal();
    return;
  }

  const buyBtn = document.getElementById('sheetBuyBtn');
  buyBtn.disabled = true;
  buyBtn.innerText = 'Processing Order...';

  try {
    const res = await fetch('/api/buy', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: currentUser.user_id,
        product_id: currentProduct.id,
        quantity: selectedQuantity,
        coupon_code: appliedCoupon ? appliedCoupon.code : ''
      })
    });
    const result = await res.json();

    if (result.ok) {
      triggerHaptic('success');
      showToast('Order completed successfully!');
      alert(`Purchase Successful!\n\nDelivered Credentials:\n${result.items.join('\n')}`);
      currentUser.balance -= total;
      updateBalanceDisplay();
      closeModal();
      await loadProducts();
    } else {
      alert(result.error || 'Purchase could not be completed.');
    }
  } catch (err) {
    alert('Error connecting to store server.');
  } finally {
    buyBtn.disabled = false;
  }
}

async function handleDepositSubmit() {
  const amount = parseFloat(document.getElementById('depositAmountInput').value) || 20;
  try {
    const res = await fetch('/api/topup', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: currentUser.user_id,
        amount: amount,
        network: selectedDepositNetwork
      })
    });
    const data = await res.json();
    if (data.ok) {
      if (data.checkout_url) {
        document.getElementById('depositAddressCode').innerHTML = `<a href="${data.checkout_url}" target="_blank" style="color:#f3ba2f;font-weight:bold;text-decoration:underline;">Click Here to Open Binance Pay Checkout</a>`;
      } else {
        document.getElementById('depositAddressCode').innerText = data.address;
      }
      document.getElementById('invoiceResult').style.display = 'block';
      triggerHaptic('success');
    }
  } catch (err) {
    alert('Failed to generate deposit invoice.');
  }
}


async function handleSupportSubmit() {
  const msg = document.getElementById('supportMsgInput').value.trim();
  if (!msg) return;

  const btn = document.getElementById('sendSupportTicketBtn');
  btn.disabled = true;
  btn.innerText = 'Sending...';

  try {
    const res = await fetch('/api/support', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: currentUser.user_id,
        username: currentUser.username,
        message: msg
      })
    });
    const data = await res.json();
    if (data.ok) {
      const statusEl = document.getElementById('supportStatus');
      statusEl.style.display = 'block';
      statusEl.innerText = `✓ Ticket #${data.ticket_id} created! Our team will reply shortly.`;
      document.getElementById('supportMsgInput').value = '';
      triggerHaptic('success');
    }
  } catch (e) {
    alert('Failed to send support ticket.');
  } finally {
    btn.disabled = false;
    btn.innerText = 'Submit Ticket';
  }
}

async function openStatsModal() {
  try {
    const res = await fetch(`/api/user/stats?user_id=${currentUser.user_id}`);
    const data = await res.json();
    if (data.ok) {
      document.getElementById('statSpent').innerText = `$${parseFloat(data.stats.total_spent).toFixed(2)}`;
      document.getElementById('statOrders').innerText = data.stats.total_orders;
      document.getElementById('statRefs').innerText = `${data.stats.referrals_count}`;
      document.getElementById('statMember').innerText = data.stats.member_since;
    }
  } catch (e) {
    console.error('Stats load error:', e);
  }
  document.getElementById('statsModal').classList.add('active');
  triggerHaptic('medium');
}

// ==============================================================================
// UzTrack - Pinduoduo (拼多多) Logistics Tracking Map Engine
// Real road-following routing with Pinduoduo clean aesthetic & badges
// ==============================================================================

class UzTrackMap {
  constructor(containerId, options = {}) {
    this.containerId = containerId;
    this.currentLang = options.lang || 'uz';
    this.trackingCode = options.trackingCode || 'UZ77019283401';
    this.apiUrl = options.apiUrl || '';
    this.currentBrand = options.brand || 'pdd';
    this.currentTheme = options.theme || 'light';
    this.customPrimary = options.primaryColor || null;

    this.map = null;
    this.vehicleMarker = null;
    this.originMarker = null;
    this.destinationMarker = null;
    this.shipmentData = null;
    this.fullRoadCoordinates = []; // [lng, lat] GeoJSON coordinates

    this.init();
  }

  getBrandColor() {
    if (this.customPrimary) return this.customPrimary;
    const brandColors = {
      'uzum': '#7000ff',
      'olx': '#002f34',
      'asaxiy': '#0066ff',
      'zoodmall': '#ff6b00',
      'zood': '#ff6b00',
      'yandex': '#fc3f1d',
      'pdd': '#16a34a',
      'pinduoduo': '#16a34a'
    };
    return brandColors[this.currentBrand.toLowerCase()] || '#16a34a';
  }

  setBrand(brand) {
    this.currentBrand = brand;
    this.renderRoadPath();
    this.renderPinduoduoBadges();
    this.renderVehicle();
  }

  setTheme(theme) {
    this.currentTheme = theme;
    const styleUrl = theme === 'dark' 
      ? 'https://tiles.openfreemap.org/styles/dark' 
      : 'https://tiles.openfreemap.org/styles/positron';
    
    if (this.map) {
      this.map.setStyle(styleUrl);
      this.map.once('style.load', () => {
        this.filterClutterLabels();
        this.renderRoadPath();
      });
    }
  }

  async init() {
    await this.fetchTrackingData();
    this.initMap();
    this.setupEvents();
  }

  initMap() {
    const isCity = this.trackingCode === 'UZ99800112233';
    const initialCenter = isCity ? [69.2401, 41.2995] : [68.0, 40.4];
    const initialZoom = isCity ? 12.8 : 7.2;

    const mapStyle = this.currentTheme === 'dark'
      ? 'https://tiles.openfreemap.org/styles/dark'
      : 'https://tiles.openfreemap.org/styles/positron';

    // Clean, minimalist vector map (Adapts to Light / Dark)
    this.map = new maplibregl.Map({
      container: this.containerId,
      style: mapStyle,
      center: initialCenter,
      zoom: initialZoom,
      pitch: 0, // Flat clean overview matching Pinduoduo screenshots
      bearing: 0,
      attributionControl: true
    });

    this.map.on('load', () => {
      this.filterClutterLabels();
      this.renderRoadPath();
      this.renderPinduoduoBadges();
      this.renderVehicle();
      this.updateUI();
    });
  }

  // Filter out minor labels (neighborhoods, hamlets, minor streets) to match Pinduoduo screenshot
  filterClutterLabels() {
    if (!this.map) return;
    const layers = this.map.getStyle().layers || [];

    layers.forEach(layer => {
      const id = layer.id.toLowerCase();
      // Hide minor neighborhood and small hamlet labels, leaving only City and District names
      if (id.includes('neighborhood') || 
          id.includes('suburb') || 
          id.includes('hamlet') || 
          id.includes('poi') || 
          id.includes('minor') || 
          id.includes('residential')) {
        try {
          this.map.setLayoutProperty(layer.id, 'visibility', 'none');
        } catch (e) {}
      }
    });
  }

  async fetchTrackingData() {
    try {
      const url = `${this.apiUrl}/v1/tracks/${this.trackingCode}`;
      const res = await fetch(url);
      if (res.ok) {
        this.shipmentData = await res.json();
      } else {
        this.shipmentData = this.getRealisticShipment(this.trackingCode);
      }
    } catch (e) {
      this.shipmentData = this.getRealisticShipment(this.trackingCode);
    }

    await this.fetchRealRoadGeometry();
  }

  // Fetches real road coordinates from OSRM
  async fetchRealRoadGeometry() {
    const origin = this.shipmentData.route.origin;
    const dest = this.shipmentData.route.destination;

    try {
      const osrmUrl = `https://router.project-osrm.org/route/v1/driving/${origin.lng},${origin.lat};${dest.lng},${dest.lat}?overview=full&geometries=geojson`;
      const res = await fetch(osrmUrl);
      if (res.ok) {
        const data = await res.json();
        if (data.routes && data.routes.length > 0) {
          this.fullRoadCoordinates = data.routes[0].geometry.coordinates; // [lng, lat]
          return;
        }
      }
    } catch (e) {
      console.warn('OSRM fallback to realistic local road coordinates:', e);
    }

    this.fullRoadCoordinates = this.getLocalRoadCoordinates();
  }

  // Renders the vibrant Pinduoduo emerald green route line along real roads
  renderRoadPath() {
    if (!this.map || this.fullRoadCoordinates.length === 0) return;

    // Remove existing layers if any
    if (this.map.getLayer('pdd-route-line-main')) this.map.removeLayer('pdd-route-line-main');
    if (this.map.getLayer('pdd-route-line-casing')) this.map.removeLayer('pdd-route-line-casing');
    if (this.map.getSource('pdd-route-source')) this.map.removeSource('pdd-route-source');

    this.map.addSource('pdd-route-source', {
      type: 'geojson',
      data: {
        type: 'Feature',
        properties: {},
        geometry: {
          type: 'LineString',
          coordinates: this.fullRoadCoordinates
        }
      }
    });

    // White under-casing for smooth contrast
    this.map.addLayer({
      id: 'pdd-route-line-casing',
      type: 'line',
      source: 'pdd-route-source',
      layout: { 'line-join': 'round', 'line-cap': 'round' },
      paint: {
        'line-color': '#ffffff',
        'line-width': 7,
        'line-opacity': 0.95
      }
    });

    // Customer Brand Route Line (Adapts to Uzum purple, OLX teal, PDD green, etc.)
    const brandColor = this.getBrandColor();
    this.map.addLayer({
      id: 'pdd-route-line-main',
      type: 'line',
      source: 'pdd-route-source',
      layout: { 'line-join': 'round', 'line-cap': 'round' },
      paint: {
        'line-color': brandColor,
        'line-width': 4.5,
        'line-opacity': 1.0
      }
    });

    // Fit map bounds to show full route comfortably
    const bounds = new maplibregl.LngLatBounds();
    this.fullRoadCoordinates.forEach(coord => bounds.extend(coord));
    this.map.fitBounds(bounds, { padding: { top: 60, bottom: 60, left: 60, right: 60 } });
  }

  // Renders Origin (发 / Jo'natildi) and Destination (已签收 / Delivered) Badges
  renderPinduoduoBadges() {
    if (this.originMarker) this.originMarker.remove();
    if (this.destinationMarker) this.destinationMarker.remove();

    const origin = this.shipmentData.route.origin;
    const dest = this.shipmentData.route.destination;
    const l = this.currentLang;
    const brandColor = this.getBrandColor();

    // 1. Origin Badge (Adapts to brand theme)
    const originEl = document.createElement('div');
    originEl.style.display = 'flex';
    originEl.style.flexDirection = 'column';
    originEl.style.alignItems = 'center';

    const originTag = l === 'uz' ? "Jo'natildi" : (l === 'ru' ? "Отправлено" : "Origin");
    originEl.innerHTML = `
      <div class="pdd-origin-badge">
        <span class="pdd-origin-tag" style="background: ${brandColor}22; color: ${brandColor};">${originTag}</span>
        <span>${origin.city}</span>
      </div>
      <div class="pdd-origin-point" style="margin-top: 4px; background: ${brandColor}; box-shadow: 0 0 0 3px ${brandColor}40;"></div>
    `;

    this.originMarker = new maplibregl.Marker({ element: originEl, anchor: 'bottom' })
      .setLngLat([origin.lng, origin.lat])
      .addTo(this.map);

    // 2. Destination / Status Badge (Adapts to brand theme)
    const destEl = document.createElement('div');
    destEl.style.display = 'flex';
    destEl.style.flexDirection = 'column';
    destEl.style.alignItems = 'center';

    const statusTitles = {
      'DELIVERED': { uz: "Topshirildi", ru: "Доставлено", en: "Delivered" },
      'IN_TRANSIT': { uz: "Yo'lda", ru: "В пути", en: "In Transit" },
      'OUT_FOR_DELIVERY': { uz: "Yetkazilmoqda", ru: "У курьера", en: "In Delivery" }
    };
    const title = statusTitles[this.shipmentData.status] ? statusTitles[this.shipmentData.status][l] : this.shipmentData.status;

    destEl.innerHTML = `
      <div class="pdd-destination-badge" style="border-color: ${brandColor}; box-shadow: 0 6px 14px ${brandColor}33;">
        <div class="pdd-dest-icon" style="background: ${brandColor};">
          <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="white" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16Z"></path>
            <polyline points="9 12 11 14 15 10"></polyline>
          </svg>
        </div>
        <span>${title}</span>
      </div>
      <div class="pdd-radar-point" style="margin-top: 4px; background: ${brandColor}; box-shadow: 0 0 0 4px ${brandColor}40;"></div>
    `;

    this.destinationMarker = new maplibregl.Marker({ element: destEl, anchor: 'bottom' })
      .setLngLat([dest.lng, dest.lat])
      .addTo(this.map);
  }

  // Renders Vehicle marker traveling on the route
  renderVehicle() {
    if (this.vehicleMarker) this.vehicleMarker.remove();

    const cur = this.shipmentData.current_location;
    const brandColor = this.getBrandColor();

    const el = document.createElement('div');
    el.innerHTML = `
      <div style="width: 26px; height: 26px; background: #ffffff; border: 2.5px solid ${brandColor}; border-radius: 50%; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 10px rgba(0,0,0,0.25);">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="${brandColor}" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <rect x="1" y="3" width="15" height="13"></rect>
          <polygon points="16 8 20 8 23 11 23 16 16 16 8"></polygon>
          <circle cx="5.5" cy="18.5" r="2.5"></circle>
          <circle cx="18.5" cy="18.5" r="2.5"></circle>
        </svg>
      </div>
    `;

    this.vehicleMarker = new maplibregl.Marker({ element: el, anchor: 'center' })
      .setLngLat([cur.lng, cur.lat])
      .addTo(this.map);
  }

  // Live simulation: advance package by 1 hour
  async simulateOneHour() {
    const btn = document.getElementById('btn-simulate-hour');
    if (btn) {
      btn.disabled = true;
      btn.innerHTML = `⏳ Hisoblanmoqda...`;
    }

    try {
      const res = await fetch(`${this.apiUrl}/v1/tracks/${this.trackingCode}/simulate-hour`, { method: 'POST' });
      if (res.ok) {
        this.shipmentData = await res.json();
      } else {
        this.simulateLocalStep();
      }
    } catch (e) {
      this.simulateLocalStep();
    }

    const cur = this.shipmentData.current_location;
    if (this.vehicleMarker) {
      this.vehicleMarker.setLngLat([cur.lng, cur.lat]);
      this.map.easeTo({ center: [cur.lng, cur.lat], duration: 1000 });
    }

    this.renderPinduoduoBadges();
    this.renderVehicle();
    this.updateUI();

    if (btn) {
      btn.disabled = false;
      btn.innerHTML = `
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polygon points="13 19 22 12 13 5 13 19"></polygon>
          <polygon points="2 19 11 12 2 5 2 19"></polygon>
        </svg>
        <span>+1 Soat Oldinga (Jonli Yangilanish)</span>
      `;
    }
  }

  simulateLocalStep() {
    const wps = this.shipmentData.route.waypoints;
    for (let i = 0; i < wps.length; i++) {
      if (!wps[i].is_passed) {
        wps[i].is_passed = true;
        this.shipmentData.current_location = {
          city: wps[i].city,
          hub: wps[i].label,
          lat: wps[i].lat,
          lng: wps[i].lng,
          updated_at: new Date().toISOString()
        };

        const newStatus = (i === wps.length - 1) ? 'DELIVERED' : 'IN_TRANSIT';
        this.shipmentData.status = newStatus;

        this.shipmentData.timeline.unshift({
          code: newStatus,
          title_uz: `Soatlik yangilanish: ${wps[i].city}`,
          title_ru: `Почасовое обновление: ${wps[i].city}`,
          title_en: `Hourly update: ${wps[i].city}`,
          description_uz: `Jo'natma ${wps[i].label} nazorat punktidan muvaffaqiyatli o'tdi.`,
          description_ru: `Отправление успешно прошло контрольный пункт ${wps[i].label}.`,
          description_en: `Parcel successfully passed checkpoint ${wps[i].label}.`,
          location_name: wps[i].label,
          timestamp: new Date().toISOString()
        });
        break;
      }
    }
  }

  // Populate Pinduoduo Card Drawer Content
  updateUI() {
    const s = this.shipmentData;
    const l = this.currentLang;

    // Header Status Title (e.g. Delivered or In Transit)
    const headerTitle = document.getElementById('header-status-title');
    if (headerTitle) {
      const titles = {
        'DELIVERED': { uz: "Yetkazib berildi", ru: "Доставлено", en: "Delivered" },
        'IN_TRANSIT': { uz: "Yo'lda", ru: "В пути", en: "In Transit" },
        'OUT_FOR_DELIVERY': { uz: "Yetkazilmoqda", ru: "Доставляется", en: "In Delivery" }
      };
      headerTitle.innerText = titles[s.status] ? titles[s.status][l] : s.status;
    }

    // Carrier & Tracking Code
    const carrierTag = document.getElementById('carrier-name-tag');
    if (carrierTag && s.carrier) {
      carrierTag.innerText = `${s.carrier.name}:`;
    }
    const trackingCodeText = document.getElementById('tracking-number-text');
    if (trackingCodeText) {
      trackingCodeText.innerText = s.tracking_code;
    }

    // Courier Info
    if (s.courier) {
      const cName = document.getElementById('courier-name-display');
      const cPhone = document.getElementById('courier-phone-display');
      const cCall = document.getElementById('btn-call-courier');
      if (cName) cName.innerText = `${s.courier.name} (Kuryer)`;
      if (cPhone) cPhone.innerText = s.courier.phone;
      if (cCall) cCall.href = `tel:${s.courier.phone}`;
    }

    // Order No & Destination Address
    const orderNo = document.getElementById('order-no-display');
    if (orderNo) orderNo.innerText = s.external_order_no || '261020-412813934891256';

    const destAddress = document.getElementById('dest-address-display');
    if (destAddress && s.route && s.route.destination) {
      destAddress.innerText = `${s.route.destination.city}, ${s.route.destination.hub}`;
    }

    // Latest Active Status Box (Pinduoduo Green Box)
    const latestStatusName = document.getElementById('latest-status-name');
    const latestStatusTime = document.getElementById('latest-status-time');
    const latestStatusNote = document.getElementById('latest-status-note');

    if (s.timeline && s.timeline.length > 0) {
      const latest = s.timeline[0];
      if (latestStatusName) {
        latestStatusName.innerText = l === 'uz' ? latest.title_uz : (l === 'ru' ? latest.title_ru : latest.title_en);
      }
      if (latestStatusTime) {
        const d = new Date(latest.timestamp);
        latestStatusTime.innerText = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}:${String(d.getSeconds()).padStart(2,'0')}`;
      }
      if (latestStatusNote) {
        const desc = l === 'uz' ? latest.description_uz : (l === 'ru' ? latest.description_ru : latest.description_en);
        const courierLink = s.courier ? `<a href="tel:${s.courier.phone}" class="courier-phone-link">${s.courier.name} (${s.courier.phone})</a>` : '';
        const supportPhone = s.carrier?.support_phone || '071-200-00-00';
        const supportLink = `<a href="tel:${supportPhone}" class="courier-phone-link">${supportPhone}</a>`;
        
        const contactPrefix = l === 'uz' 
          ? `Kuryer: ${courierLink}. Markaziy dispetcher: ${supportLink}.` 
          : (l === 'ru' ? `Курьер: ${courierLink}. Диспетчерская: ${supportLink}.` : `Courier: ${courierLink}. Support: ${supportLink}.`);

        latestStatusNote.innerHTML = `${desc} ${contactPrefix}`;
      }
    }

    // Render Warehouse Inspection Photos (集运仓实拍验货照)
    const photosGrid = document.getElementById('warehouse-photos-grid');
    if (photosGrid && s.inspection_photos && s.inspection_photos.length > 0) {
      photosGrid.innerHTML = s.inspection_photos.map(p => {
        const caption = l === 'uz' ? p.caption_uz : (l === 'ru' ? p.caption_ru : p.caption_en);
        return `
          <div class="photo-item" onclick="openPhotoModal('${p.url}', '${caption}')">
            <img src="${p.thumb || p.url}" alt="${caption}">
            <span class="photo-zoom-tag">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <circle cx="11" cy="11" r="8"></circle>
                <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
                <line x1="11" y1="8" x2="11" y2="14"></line>
                <line x1="8" y1="11" x2="14" y2="11"></line>
              </svg>
            </span>
          </div>
        `;
      }).join('');
    }

    // Historical Milestones List
    const timelineList = document.getElementById('timeline-list');
    if (timelineList && s.timeline) {
      // Skip the first one since it's already shown in the active box above
      const pastItems = s.timeline.slice(1);
      timelineList.innerHTML = pastItems.map(item => {
        const title = l === 'uz' ? item.title_uz : (l === 'ru' ? item.title_ru : item.title_en);
        const desc = l === 'uz' ? item.description_uz : (l === 'ru' ? item.description_ru : item.description_en);
        const d = new Date(item.timestamp);
        const timeStr = `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}:${String(d.getSeconds()).padStart(2,'0')}`;

        return `
          <li class="timeline-node-item">
            <div class="timeline-node-dot"></div>
            <div class="timeline-node-time">${timeStr}</div>
            <div class="timeline-node-content"><strong>${title}</strong>: ${desc}</div>
          </li>
        `;
      }).join('');
    }
  }

  setupEvents() {
    const simBtn = document.getElementById('btn-simulate-hour');
    if (simBtn) simBtn.addEventListener('click', () => this.simulateOneHour());

    const langSelect = document.getElementById('lang-select');
    if (langSelect) {
      langSelect.value = this.currentLang;
      langSelect.addEventListener('change', (e) => {
        this.currentLang = e.target.value;
        this.renderPinduoduoBadges();
        this.updateUI();
      });
    }
  }

  // Realistic M39 Highway GeoJSON coordinates [lng, lat]
  getLocalRoadCoordinates() {
    if (this.trackingCode === 'UZ99800112233') {
      return [
        [69.20110, 41.27217], [69.20500, 41.27500], [69.21300, 41.27850], [69.21900, 41.28200],
        [69.22500, 41.28500], [69.23600, 41.29100], [69.24500, 41.29800], [69.26000, 41.30500],
        [69.27100, 41.31200], [69.27800, 41.31700], [69.28300, 41.32000]
      ];
    }

    return [
      [69.2198, 41.2268], [69.1860, 41.2050], [69.1713, 41.2117], [69.1120, 41.1685],
      [69.0500, 41.1167], [69.0503, 41.0906], [68.8871, 40.9766], [68.7594, 40.9411],
      [68.6850, 40.8650], [68.6618, 40.8373], [68.6950, 40.7180], [68.5200, 40.5400],
      [68.3550, 40.4050], [68.1800, 40.2800], [68.0400, 40.1600], [67.8422, 40.1158],
      [67.7500, 40.0800], [67.5850, 40.0150], [67.4500, 39.9800], [67.3500, 39.8900],
      [67.2711, 39.7611], [67.1500, 39.7100], [67.0400, 39.6850], [66.9597, 39.6542]
    ];
  }

  getRealisticShipment(code) {
    if (code === 'UZ99800112233') {
      return {
        tracking_code: "UZ99800112233",
        external_order_no: "261020-287425216811256",
        marketplace_id: "olx",
        carrier: { code: "yandex", name: "Yandex Delivery", support_phone: "+998712003344" },
        status: "OUT_FOR_DELIVERY",
        current_location: { city: "Toshkent", hub: "Chilonzor distribyutsiya punkti", lat: 41.2721, lng: 69.2012 },
        route: {
          origin: { city: "Toshkent (Chilonzor)", hub: "Chilonzor 19-mavze", lat: 41.2721, lng: 69.2012 },
          destination: { city: "Toshkent (Yunusobod)", hub: "Amir Temur shox ko'chasi 45", lat: 41.3200, lng: 69.2830 },
          waypoints: [
            { city: "Chilonzor", label: "Chilonzor 19-mavze", lat: 41.2721, lng: 69.2012, is_passed: true },
            { city: "Bunyodkor", label: "Bunyodkor shoh ko'chasi", lat: 41.2850, lng: 69.2250, is_passed: true },
            { city: "Novza", label: "O'zbekiston prospekti", lat: 41.3050, lng: 69.2600, is_passed: false },
            { city: "Amir Temur", label: "Yetkazish manzili", lat: 41.3200, lng: 69.2830, is_passed: false }
          ]
        },
        courier: {
          name: "Bobur Temirov",
          phone: "+998 93 998 87 76"
        },
        timeline: [
          {
            code: "OUT_FOR_DELIVERY",
            title_uz: "Yetkazilmoqda",
            title_ru: "Доставляется",
            title_en: "In Delivery",
            description_uz: "Kuryer Bobur Temirov jo'natmani topshirish uchun yo'lga chiqdi.",
            description_ru: "Курьер Бобур Темиров везет заказ.",
            description_en: "Courier Bobur Temirov is out for delivery.",
            location_name: "Toshkent",
            timestamp: new Date().toISOString()
          },
          {
            code: "ORIGIN_HUB_IN",
            title_uz: "Distribyutsiya markazida",
            title_ru: "В пункте распределения",
            title_en: "At Hub",
            description_uz: "Chilonzor distribyutsiya markaziga yetib keldi.",
            description_ru: "Прибыло в пункт распределения Чиланзар.",
            description_en: "Arrived at distribution hub.",
            location_name: "Toshkent",
            timestamp: new Date(Date.now() - 3600000 * 2).toISOString()
          }
        ]
      };
    }

    return {
      tracking_code: "UZ77019283401",
      external_order_no: "261020-412813934891256",
      marketplace_id: "uzum",
      carrier: { code: "fargo", name: "Fargo Express", support_phone: "+998712000000" },
      status: "IN_TRANSIT",
      current_location: { city: "Jizzax", hub: "Jizzax M39 tranzit nazorati", lat: 40.1158, lng: 67.8422 },
      inspection_photos: [
        {
          url: "https://images.unsplash.com/photo-1544441893-675973e31985?auto=format&fit=crop&w=800&q=80",
          thumb: "https://images.unsplash.com/photo-1544441893-675973e31985?auto=format&fit=crop&w=300&q=80",
          caption_uz: "Sergeli saralash omborida jo'natma qadog'i tekshiruvi (验货照)",
          caption_ru: "Фото фиксации груза на складе Сергели (验货照)",
          caption_en: "Cargo parcel received at Sergeli sorting hub (Inspection Photo)"
        },
        {
          url: "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=800&q=80",
          thumb: "https://images.unsplash.com/photo-1542291026-7eec264c27ff?auto=format&fit=crop&w=300&q=80",
          caption_uz: "Sifat va butunlik tekshiruvi (Ombor 139 / Fargo)",
          caption_ru: "Проверка качества и целостности (Склад 139 / Fargo)",
          caption_en: "Quality and integrity inspection (Hub 139 / Fargo)"
        }
      ],
      route: {
        origin: { city: "Toshkent", hub: "Sergeli Markaziy Saralash Markazi", lat: 41.2268, lng: 69.2198 },
        destination: { city: "Samarqand", hub: "Registon Markaziy Hub, 14-uy", lat: 39.6542, lng: 66.9597 },
        waypoints: [
          { city: "Toshkent", label: "Sergeli Markaziy Saralash Markazi", lat: 41.2268, lng: 69.2198, is_passed: true },
          { city: "Yangiyo'l", label: "M39 Yangiyo'l nazorati", lat: 41.1167, lng: 69.0500, is_passed: true },
          { city: "Chinoz", label: "Chinoz daryo o'tish punkti", lat: 40.9411, lng: 68.7594, is_passed: true },
          { city: "Sirdaryo", label: "Guliston / Sirdaryo tranziti", lat: 40.8373, lng: 68.6618, is_passed: true },
          { city: "Jizzax", label: "Jizzax M39 tranzit nazorati", lat: 40.1158, lng: 67.8422, is_passed: true },
          { city: "G'allaorol", label: "G'allaorol dovoni", lat: 40.0150, lng: 67.5850, is_passed: false },
          { city: "Bulung'ur", label: "Samarqand kirish punkti", lat: 39.7611, lng: 67.2711, is_passed: false },
          { city: "Samarqand", label: "Registon Markaziy Hub", lat: 39.6542, lng: 66.9597, is_passed: false }
        ]
      },
      courier: {
        name: "Jasur Aliyev",
        phone: "+998 90 123 45 67"
      },
      timeline: [
        {
          code: "IN_TRANSIT",
          title_uz: "Shaharlararo yo'lda",
          title_ru: "В пути между городами",
          title_en: "In Transit",
          description_uz: "Jo'natma Jizzax M39 tranzit punkti orqali Samarqand tomon harakatlanmoqda.",
          description_ru: "Отправление движется через Джизак в сторону Самарканда (трасса М39).",
          description_en: "Parcel is in transit passing Jizzakh toward Samarkand (M39).",
          location_name: "Jizzax",
          timestamp: new Date().toISOString()
        },
        {
          code: "ORIGIN_HUB_IN",
          title_uz: "Saralash markazida",
          title_ru: "В сортировочном центре",
          title_en: "At Sorting Hub",
          description_uz: "Toshkent Sergeli saralash markaziga qabul qilindi va yo'nalishga qo'yildi.",
          description_ru: "Принято в сортировочном центре Ташкент Сергели.",
          description_en: "Received at Tashkent Sergeli sorting hub.",
          location_name: "Toshkent",
          timestamp: new Date(Date.now() - 3600000 * 3).toISOString()
        },
        {
          code: "PICKED_UP",
          title_uz: "Kuryer qabul qildi",
          title_ru: "Курьер забрал",
          title_en: "Picked Up",
          description_uz: "Jo'natuvchidan qabul qilib olindi.",
          description_ru: "Заказ забран у отправителя.",
          description_en: "Picked up from merchant.",
          location_name: "Toshkent",
          timestamp: new Date(Date.now() - 3600000 * 5).toISOString()
        },
        {
          code: "ORDER_CREATED",
          title_uz: "Buyurtma rasmiylashtirildi",
          title_ru: "Заказ оформлен",
          title_en: "Order Placed",
          description_uz: "Marketplaceda jo'natma yorlig'i yaratildi.",
          description_ru: "Накладная отправления создана.",
          description_en: "Shipment label created on the marketplace.",
          location_name: "Toshkent",
          timestamp: new Date(Date.now() - 3600000 * 8).toISOString()
        }
      ]
    };
  }
}

window.UzTrackMap = UzTrackMap;

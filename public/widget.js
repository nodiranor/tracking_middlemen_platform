/**
 * UzTrack (UZ-LTS) - Universal Embeddable Web Component & Drop-in SDK
 * Allows any Marketplace or Classifieds platform (Uzum, OLX, Asaxiy, etc.)
 * to embed real-time 3D cartoon tracking with a single HTML tag.
 * 
 * Usage:
 * <script src="https://cdn.track.uz/widget.js" async></script>
 * <uz-tracking-view tracking-code="UZ77019283401" lang="uz"></uz-tracking-view>
 */

class UzTrackingViewElement extends HTMLElement {
  connectedCallback() {
    const trackingCode = this.getAttribute('tracking-code') || this.getAttribute('code') || 'UZ77019283401';
    const apiUrl = this.getAttribute('api-url') || '';
    const lang = this.getAttribute('lang') || 'uz';
    const height = this.getAttribute('height') || '600px';
    const brand = this.getAttribute('brand') || '';
    const theme = this.getAttribute('theme') || 'light';
    const primaryColor = this.getAttribute('primary-color') || '';
    const borderRadius = this.getAttribute('border-radius') || '16px';

    this.style.display = 'block';
    this.style.width = '100%';
    this.style.height = height;
    this.style.borderRadius = borderRadius;
    this.style.overflow = 'hidden';
    this.style.boxShadow = '0 10px 25px -5px rgba(0, 0, 0, 0.1)';

    const queryParams = new URLSearchParams({
      code: trackingCode,
      lang: lang,
      embed: 'true'
    });

    if (brand) queryParams.set('brand', brand);
    if (theme) queryParams.set('theme', theme);
    if (primaryColor) queryParams.set('primary', primaryColor);

    const iframe = document.createElement('iframe');
    iframe.src = `${apiUrl}/?${queryParams.toString()}`;
    iframe.style.width = '100%';
    iframe.style.height = '100%';
    iframe.style.border = 'none';
    iframe.allow = 'geolocation';

    this.innerHTML = '';
    this.appendChild(iframe);
  }
}

if (!customElements.get('uz-tracking-view')) {
  customElements.define('uz-tracking-view', UzTrackingViewElement);
}

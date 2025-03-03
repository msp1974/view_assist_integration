export async function hass_base_el() {
  await Promise.race([
    customElements.whenDefined("home-assistant"),
    customElements.whenDefined("hc-main"),
  ]);

  const element = customElements.get("home-assistant")
    ? "home-assistant"
    : "hc-main";

  while (!document.querySelector(element))
    await new Promise((r) => window.setTimeout(r, 100));
  return document.querySelector(element);
}

export async function hass() {
  const base = await hass_base_el();
  while (!base.hass) await new Promise((r) => window.setTimeout(r, 100));
  return base.hass;
}

function strftime(sFormat, date) {
  if (!(date instanceof Date)) date = new Date();
  var nDay = date.getDay(),
    nDate = date.getDate(),
    nMonth = date.getMonth(),
    nYear = date.getFullYear(),
    nHour = date.getHours(),
    aDays = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'],
    aMonths = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'],
    aDayCount = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334],
    isLeapYear = function() {
      if ((nYear&3)!==0) return false;
      return nYear%100!==0 || nYear%400===0;
    },
    getThursday = function() {
      var target = new Date(date);
      target.setDate(nDate - ((nDay+6)%7) + 3);
      return target;
    },
    zeroPad = function(nNum, nPad) {
      return ('' + (Math.pow(10, nPad) + nNum)).slice(1);
    };
  return sFormat.replace(/%[a-z]/gi, function(sMatch) {
    return {
      '%a': aDays[nDay].slice(0,3),
      '%A': aDays[nDay],
      '%b': aMonths[nMonth].slice(0,3),
      '%B': aMonths[nMonth],
      '%c': date.toUTCString(),
      '%C': Math.floor(nYear/100),
      '%d': zeroPad(nDate, 2),
      '%e': nDate,
      '%F': date.toISOString().slice(0,10),
      '%G': getThursday().getFullYear(),
      '%g': ('' + getThursday().getFullYear()).slice(2),
      '%H': zeroPad(nHour, 2),
      '%I': zeroPad((nHour+11)%12 + 1, 2),
      '%j': zeroPad(aDayCount[nMonth] + nDate + ((nMonth>1 && isLeapYear()) ? 1 : 0), 3),
      '%k': '' + nHour,
      '%l': (nHour+11)%12 + 1,
      '%m': zeroPad(nMonth + 1, 2),
      '%M': zeroPad(date.getMinutes(), 2),
      '%p': (nHour<12) ? 'AM' : 'PM',
      '%P': (nHour<12) ? 'am' : 'pm',
      '%s': Math.round(date.getTime()/1000),
      '%S': zeroPad(date.getSeconds(), 2),
      '%u': nDay || 7,
      '%V': (function() {
              var target = getThursday(),
                n1stThu = target.valueOf();
              target.setMonth(0, 1);
              var nJan1 = target.getDay();
              if (nJan1!==4) target.setMonth(0, 1 + ((4-nJan1)+7)%7);
              return zeroPad(1 + Math.ceil((n1stThu-target)/604800000), 2);
            })(),
      '%w': '' + nDay,
      '%x': date.toLocaleDateString(),
      '%X': date.toLocaleTimeString(),
      '%y': ('' + nYear).slice(2),
      '%Y': nYear,
      '%z': date.toTimeString().replace(/.+GMT([+-]\d+).+/, '$1'),
      '%Z': date.toTimeString().replace(/.+\((.+?)\)$/, '$1')
    }[sMatch] || sMatch;
  });
}

class Clock extends HTMLElement {
  static observedAttributes = ["server_time", "format"];

  constructor() {
    super();
  }

  connectedCallback() {
    const shadow = this.shadowRoot || this.attachShadow({ mode: 'open' });
    // Create span
    this.shadowRoot.innerHTML = '';
    const el = document.createElement("span");
    el.setAttribute("class", "clock");
    shadow.appendChild(el);


    const server_time = this.getAttribute("server_time");

    this.run_clock(el, server_time);
  }

  display_time(el, server_time) {

    const dt_now = new Date();
    var format = this.getAttribute("format") ? this.getAttribute("format") : '%H:%M'

    if (server_time) {
      el.textContent = strftime(format, new Date(dt_now.getTime() + window.viewassist_time_delta));
    } else {
      el.textContent = strftime(format,dt_now);
    }
  }

  run_clock(el, server_time) {
    var t = this;
    t.display_time(el, server_time);
    const x = setInterval(function () {
      t.display_time(el, server_time);
    }, 1000);
  }
}

class CountdownTimer extends HTMLElement {
  static observedAttributes = ["expires"];

  constructor() {
    super();
  }

  connectedCallback() {
    const shadow = this.shadowRoot || this.attachShadow({ mode: 'open' });
    // Create span
    this.shadowRoot.innerHTML = '';
    const el = document.createElement("span");
    el.setAttribute("class", "countdown");
    shadow.appendChild(el);


    const expires = this.getAttribute("expires");
    this.start_timer(el, expires);
  }

  display_countdown(el, expires) {
    // Get today's date and time
    var now = new Date().getTime();

    var expire = new Date(expires).getTime();

    // Find the distance between now and the count down date
    var distance = expire - now;

    // Time calculations for days, hours, minutes and seconds
    var days = Math.floor(distance / (1000 * 60 * 60 * 24));
    var hours = String(Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60))).padStart(2,'0');
    var minutes = String(Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60))).padStart(2,'0');
    var seconds = String(Math.floor((distance % (1000 * 60)) / 1000)).padStart(2,'0');

    // Display the result in the element
    if (days) {
      el.textContent = days + "d " + hours + ":" + minutes + ":" + seconds;
    } else {
      el.textContent = hours + ":" + minutes + ":" + seconds;
    }
    return distance
  }

  start_timer(el, expires) {
    if (expires != 0) {
      var t = this;
      t.display_countdown(el, expires)
      const x = setInterval(function () {
        var distance = t.display_countdown(el, expires);
        if (distance < 0) {
          clearInterval(x);
          el.textContent = "Expired";
        }
      }, 500);
    } else {
      if (typeof x !== 'undefined') { clearInterval(x) };
      el.textContent = "No Timers";
    }
  }
}


class ViewAssist {
  constructor(hass) {
    this.hass = hass
    this.va_entity = '';
    this.display_index = -1;
    this.initializeWhenReady();
  }

  async initializeWhenReady(attempts = 0) {
    if (attempts > 50) {
      console.log("Failed to initialize after 50 attempts");
      return;
    }

    try {
      await this.set_va_entity();
      await this.set_time_delta();

      console.info(
        `%cVIEW ASSIST ${version} IS INSTALLED
          %cView Assist Entity: ${this.va_entity}
          Display Index: ${this.display_index}
          Time Delta: ${window.viewassist_time_delta}`,
          "color: green; font-weight: bold",
          ""
      );


      const bc = await Promise.resolve(customElements.whenDefined("button-card"))
      if (!bc) {
        throw new Error("No button-card element");
      }

      customElements.define("viewassist-countdown", CountdownTimer)
      customElements.define("viewassist-clock", Clock)

      // Update time delta
      var t = this;
      const delta = setInterval(function () {
        t.set_time_delta();
      }, 300 * 1000);

    } catch (e) {
      console.log("Initialization retry:", e.message);
      setTimeout(() => this.initializeWhenReady(attempts + 1), 100);
    }
  }

  async set_va_entity() {
    var response = await this.hass.callWS({
      type: 'view_assist/get_entity_id',
      browser_id: localStorage.getItem("browser_mod-browser-id")
    })
    this.va_entity = response.entity_id
    this.display_index = response.display_index
    localStorage.setItem("view_assist_sensor", this.va_entity);
    localStorage.setItem("view_assist_display_index", this.display_index);

  }

  async set_time_delta() {
    const delta = await this.hass.callWS({
      type: 'view_assist/get_server_time_delta',
      epoch: new Date().getTime()
    })
    window.viewassist_time_delta = delta;
  }
}


const version = "1.0.2"

// Get the view asssit entity for this browser id and save in local storage


// Initialize when core web components are ready
const ha = await hass();

Promise.all([
  customElements.whenDefined("home-assistant"),
  customElements.whenDefined("hui-view")
]).then(() => {
  window.ViewAssist = new ViewAssist(ha);
});

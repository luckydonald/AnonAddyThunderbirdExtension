Perfect! I have all the files. Now let me extract the exact sections you requested:

## Report: Exact Content of Specified Code Sections

### 1. `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/src/experiment/implementation.js`

**Lines 253-310** (onContextMenu and onPopupShowing functions):
```javascript
253	      menu.appendChild(menuPopup);
254	      return menu;
255	    }
256	
257	    function attachToWindow(win) {
258	      if (attached.has(win)) return;
259	      const doc = win.document;
260	
261	      let pendingPill = null;
262	      let pendingReset = null;
263	
264	      function onContextMenu(e) {
265	        // composedPath() crosses shadow-DOM boundaries; closest() does not.
266	        const pill = e.composedPath().find(
267	          (el) => el.tagName && el.tagName.toLowerCase() === "mail-address-pill",
268	        ) ?? null;
269	        if (!pill) {
270	          pendingPill = null;
271	          return;
272	        }
273	        // Skip Reply-To pills — Addy alias sending doesn't apply there.
274	        const addressRow = pill.closest(".address-row");
275	        const fieldType = (addressRow?.dataset?.recipienttype || "").toLowerCase();
276	        if (fieldType === "reply-to" || fieldType === "replyto") {
277	          pendingPill = null;
278	          return;
279	        }
280	        pendingPill = pill;
281	        clearTimeout(pendingReset);
282	        pendingReset = setTimeout(() => {
283	          pendingPill = null;
284	        }, 500);
285	      }
286	
287	      function onPopupShowing(e) {
288	        if (!pendingPill) return;
289	        const popup = e.target;
290	        if (popup.tagName.toLowerCase() !== "menupopup") return;
291	
292	        const pill = pendingPill;
293	        pendingPill = null;
294	        clearTimeout(pendingReset);
295	
296	        const sep = doc.createXULElement("menuseparator");
297	        const addyMenu = buildAddyMenu(doc, win, pill);
298	
299	        popup.appendChild(sep);
300	        popup.appendChild(addyMenu);
301	
302	        popup.addEventListener(
303	          "popuphidden",
304	          () => {
305	            sep.remove();
306	            addyMenu.remove();
307	          },
308	          { once: true },
309	        );
310	      }
```

**Lines 100-135** (buildAddyMenu top section):
```javascript
100	    function buildAddyMenu(doc, win, pill) {
101	      const email = pill.getAttribute("emailAddress") || "";
102	      const displayName = pill.getAttribute("displayName") || "";
103	      const addressRow = pill.closest(".address-row");
104	      const fieldType = (addressRow?.dataset?.recipienttype || "to").toLowerCase();
105	
106	      const availableDomains = _cacheData.domainOptions?.data || [];
107	      const defaultDomain =
108	        _cacheData.domainOptions?.defaultAliasDomain ||
109	        availableDomains[0] ||
110	        "";
111	      const existingAliases = matchingAliasesForEmail(email);
112	
113	      // Top-level menu entry — direct click opens popup, hover/arrow unfolds submenu.
114	      const menu = doc.createXULElement("menu");
115	      const menuPopup = doc.createXULElement("menupopup");
116	      menu.setAttribute("label", "Use Addy alias for sending");
117	      const menuPopup = doc.createXULElement("menupopup");
118	
119	      // Direct click on the <menu> element itself (not on a submenu item) opens popup.
120	      menu.addEventListener("click", (e) => {
121	        if (e.target === menu) {
122	          chipMenuFire &&
123	            chipMenuFire.async({ email, displayName, fieldType, action: "open_popup" });
124	          e.preventDefault();
125	        }
126	      });
127	
128	      // ── Existing… ▶ ──────────────────────────────────────────────────────────
129	      const existingMenu = doc.createXULElement("menu");
130	      existingMenu.setAttribute("label", "Existing…");
131	      const existingPopup = doc.createXULElement("menupopup");
132	
133	      // "Open alias picker…" is first in Existing; provides easy access to full GUI.
134	      const pickerItem = doc.createXULElement("menuitem");
135	      pickerItem.setAttribute("label", "Open alias picker…");
```

### 2. `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/src/popup/components/CreateAliasForm.vue`

**Lines 55-75** (forwardingPreview / sendsAsPreview computed properties):
```javascript
55	    return customPrefix.value.trim() || "[custom]";
56	  }
57	  return FORMAT_PLACEHOLDERS[format.value] || "[alias]";
58	});
59	
60	const forwardingPreview = computed(() => {
61	  const m = props.targetEmail.match(/^(.+)@(.+)$/);
62	  if (!m) return null;
63	  const [, targetLocal, targetDomain] = m;
64	  return `${aliasLocalPreview.value}+${targetLocal}=${targetDomain}@${domain.value}`;
65	});
66	
67	const sendsAsPreview = computed(() => {
68	  if (!forwardingPreview.value) return null;
69	  return props.targetName
70	    ? `${props.targetName} <${forwardingPreview.value}>`
71	    : forwardingPreview.value;
72	});
```

**Lines 195-215** (preview template section):
```vue
200	    <!-- "Sends via:" only when name is present (forwarding addr buried in Sends as:) -->
201	    <p v-if="forwardingPreview && targetName" class="preview">
202	      <span class="preview-label">{{ t("aliasPreviewLabel") }}</span>
203	      <code class="preview-address">{{ forwardingPreview }}</code>
204	    </p>
205	    <!-- "Sends as:" always when preview available -->
206	    <p v-if="sendsAsPreview" class="preview">
207	      <span class="preview-label">{{ t("aliasDisplayLabel") }}</span>
208	      <code class="preview-address">{{ sendsAsPreview }}</code>
209	    </p>
210	  </div>
211	</template>
212	
213	<style scoped lang="scss">
214	@use "../styles/variables" as *;
215	
```

**Lines 126-160** (combobox domain picker template):
```vue
126	      <div class="combobox" @keydown="onComboboxKey">
127	        <button
128	          type="button"
129	          class="combobox__trigger"
130	          @click="openCombobox"
131	        >
132	          <span>{{ domain }}</span>
133	          <span class="combobox__arrow">▾</span>
134	        </button>
135	        <div v-if="comboboxOpen" class="combobox__dropdown">
136	          <input
137	            ref="searchInput"
137	            v-model="domainSearch"
138	            type="text"
139	            :placeholder="t('filterDomains')"
140	            class="combobox__search"
141	            @blur.self="comboboxOpen = false"
142	          />
143	          <ul class="combobox__list">
144	            <li
145	              v-for="(d, i) in filteredDomains"
146	              :key="d"
147	              class="combobox__option"
148	              :class="{ selected: domain === d, active: i === comboboxActiveIdx }"
149	              @mousedown.prevent="selectDomain(d)"
150	            >
151	              {{ d }}
152	            </li>
153	          </ul>
154	        </div>
155	      </div>
156	    </div>
157	
158	    <div class="field">
159	      <label>{{ t("format") }}</label>
160	      <div class="format-pills">
161	```

**Lines 36-45** (filteredDomains computed):
```javascript
36	const filteredDomains = computed(() => {
37	  const q = domainSearch.value.toLowerCase();
38	  return q
39	    ? props.availableDomains.filter((d) => d.toLowerCase().includes(q))
40	    : props.availableDomains;
41	});
42	
43	const formats = computed((): { value: AliasFormat; label: string }[] => [
44	  { value: "random_characters", label: t("formatCharacters") },
45	  { value: "random_words", label: t("formatWords") },
```

### 3. `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/src/popup/components/RecipientCard.vue`

**Lines 86-180** (full alias-list section in template):
```vue
86	
87	    <!-- Existing aliases section (always visible) -->
88	    <p class="section-heading">{{ t("existingAliasesSection") }}</p>
89	
90	    <div class="alias-list">
91	      <!-- Created alias pinned at top with inline manage controls -->
92	      <div
93	        v-if="createdAlias"
94	        class="alias-option alias-option--created"
95	        :class="{ selected: selectedAlias === createdAlias.email }"
96	        @click="!createdAlias.active || selectAlias(createdAlias.email)"
97	      >
98	        <input
99	          type="radio"
100	          :name="`alias-${address}`"
101	          :value="createdAlias.email"
102	          :checked="selectedAlias === createdAlias.email"
103	          :disabled="!createdAlias.active"
104	          @change="selectAlias(createdAlias.email)"
105	        />
106	        <div class="alias-option__body">
107	          <div class="alias-option__row">
108	            <kbd
109	              class="alias-option__email"
110	              :class="{ 'alias-option__email--inactive': !createdAlias.active }"
111	            >{{ createdAlias.email }}</kbd>
112	            <span class="tag tag--new">{{ t("newTag") }}</span>
113	            <span v-if="!createdAlias.active" class="tag tag--inactive">{{ t("inactive") }}</span>
114	          </div>
115	          <div class="alias-option__actions" @click.stop>
116	            <button
117	              v-if="createdAlias.active"
118	              class="small danger"
119	              :title="t('disableHint')"
120	              @click="$emit('disable')"
121	            >{{ t("disable") }}</button>
122	            <button
123	              v-else
124	              class="small"
125	              :title="t('disableHint')"
126	              @click="$emit('restore')"
127	            >{{ t("reenable") }}</button>
128	            <button
129	              class="small danger"
130	              :title="t('deleteHint')"
131	              @click="$emit('delete')"
132	            >{{ t("deleteAlias") }}</button>
133	          </div>
134	        </div>
135	      </div>
136	
137	      <!-- Regular existing aliases -->
138	      <label
139	        v-for="alias in displayAliases"
140	        :key="alias.id"
141	        class="alias-option"
141	        :class="{ selected: selectedAlias === alias.email }"
142	      >
143	        <input
144	          type="radio"
145	          :name="`alias-${address}`"
146	          :value="alias.email"
147	          :checked="selectedAlias === alias.email"
148	          @change="selectAlias(alias.email)"
149	        />
150	        <kbd class="alias-option__email">{{ alias.email }}</kbd>
151	        <span v-if="alias.description" class="alias-option__desc">
152	          {{ alias.description }}
153	        </span>
154	      </label>
155	
156	      <!-- Empty state -->
157	      <div v-if="!createdAlias && displayAliases.length === 0" class="no-aliases">
158	        <em>{{ t("noExistingAliases") }}</em>
159	      </div>
160	
161	      <!-- Don't replace option -->
162	      <label
163	        v-if="createdAlias || displayAliases.length > 0"
163	        class="alias-option alias-option--none"
164	        :class="{ selected: selectedAlias === null }"
165	      >
166	        <input
167	          type="radio"
168	          :name="`alias-${address}`"
169	          :checked="selectedAlias === null"
170	          @change="$emit('update:selectedAlias', null)"
171	        />
172	        <span>{{ t("dontReplace") }}</span>
173	      </label>
174	    </div>
175	
176	    <!-- Create new alias section (always visible) -->
177	    <CreateAliasForm
178	      :available-domains="availableDomains"
179	      :default-domain="defaultDomain"
180	      :default-format="defaultFormat"
```

### 4. `/home/user/git/luckydonald/AnonAddyThunderbirdExtension/src/popup/App.vue`

**Lines 80-95** (matchingAliases function):
```javascript
83	function matchingAliases(aliases: Alias[], domain: string): Alias[] {
84	  const lower = domain.toLowerCase();
85	  const matched = aliases.filter(
86	    (a) =>
87	      a.active &&
88	      (a.email.toLowerCase().includes(lower) ||
89	        (a.description ?? "").toLowerCase().includes(lower)),
90	  );
91	  // Sort: aliases whose address contains the domain first
92	  matched.sort((a) =>
93	    a.email.toLowerCase().startsWith(lower.split(".")[0]) ? -1 : 1,
94	  );
95	  return matched.slice(0, 10);
```

All sections have been extracted with exact line numbers as requested.
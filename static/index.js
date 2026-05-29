window.PageNostrBunker = {
  template: '#page-nostr_bunker',
  delimiters: ['${', '}'],
  data: function () {
    return {
      currencyOptions: ['sat'],
      relayOptions: [
        'wss://relay.damus.io',
        'wss://nos.lol',
        'wss://relay.primal.net',
        'wss://relay.nostr.band'
      ],
      permissionOptions: [
        'get_public_key',
        'ping',
        'nip04_encrypt',
        'nip04_decrypt',
        'nip44_encrypt',
        'nip44_decrypt',
        'switch_relays',
        'sign_event:0',
        'sign_event:1',
        'sign_event:3',
        'sign_event:4',
        'sign_event:5',
        'sign_event:6',
        'sign_event:7',
        'sign_event:14',
        'sign_event:1059'
      ],
      capabilityOptions: [
        {label: 'Read profile', value: 'read_profile'},
        {label: 'Update profile', value: 'sign_profile'},
        {label: 'Read follows', value: 'read_follows'},
        {label: 'Update follows', value: 'sign_follows'},
        {label: 'Read posts', value: 'read_posts'},
        {label: 'Sign posts', value: 'sign_posts'},
        {label: 'Delete posts', value: 'delete_posts'},
        {label: 'Repost posts', value: 'repost_posts'},
        {label: 'React to posts', value: 'react_posts'},
        {label: 'Read DMs', value: 'read_dms'},
        {label: 'Sign DMs', value: 'sign_dms'}
      ],
      settingsFormDialog: {
        show: false,
        data: {}
      },

      bunkersDataFormDialog: {
        show: false,
        data: {
          name: null,
          nsec: null
        }
      },
      bunkersDataList: [],
      bunkersDataTable: {
        search: '',
        loading: false,
        columns: [
          {"name": "name", "align": "left", "label": "Name", "field": "name", "sortable": true},
          {"name": "nsec", "align": "left", "label": "Nsec", "field": "nsec", "sortable": true},
          {"name": "updated_at", "align": "left", "label": "Updated At", "field": "updated_at", "sortable": true},
          {"name": "id", "align": "left", "label": "ID", "field": "id", "sortable": true},
          
        ],
        pagination: {
          sortBy: 'updated_at',
          rowsPerPage: 10,
          page: 1,
          descending: true,
          rowsNumber: 10
        }
      },

      urlDataFormDialog: {
        show: false,
        bunkersData: {label: 'All Bunkers Data', value: ''},
        data: {}
      },
      urlDataList: [],
      urlDataTable: {
        search: '',
        loading: false,
        columns: [
          {"name": "name", "align": "left", "label": "Name", "field": "name", "sortable": true},
          {"name": "relays", "align": "left", "label": "Relays", "field": row => (row.relays || []).join(', '), "sortable": false},
          {"name": "permissions", "align": "left", "label": "Permissions", "field": "permissions", "sortable": true},
          {"name": "auto_sign", "align": "left", "label": "Auto", "field": "auto_sign", "sortable": true},
          {"name": "confirm_sign", "align": "left", "label": "Confirm", "field": "confirm_sign", "sortable": true},
          {"name": "expires_at", "align": "left", "label": "Expires", "field": "expires_at", "sortable": true},
          {"name": "can_read", "align": "left", "label": "Read", "field": "can_read", "sortable": true},
          {"name": "can_write", "align": "left", "label": "Write", "field": "can_write", "sortable": true},
          {"name": "post_rate_limit_per_day", "align": "left", "label": "Daily Limit", "field": "post_rate_limit_per_day", "sortable": true},
          {"name": "updated_at", "align": "left", "label": "Updated At", "field": "updated_at", "sortable": true},
          {"name": "id", "align": "left", "label": "ID", "field": "id", "sortable": true},
          
        ],
        pagination: {
          sortBy: 'updated_at',
          rowsPerPage: 10,
          page: 1,
          descending: true,
          rowsNumber: 10
        }
      },

      signingRequestList: [],
      signingRequestTable: {
        search: '',
        loading: false,
        columns: [
          {"name": "request_id", "align": "left", "label": "Request", "field": "request_id", "sortable": true},
          {"name": "client_pubkey", "align": "left", "label": "Client", "field": "client_pubkey", "sortable": true},
          {"name": "status", "align": "left", "label": "Status", "field": "status", "sortable": true},
          {"name": "expires_at", "align": "left", "label": "Expires", "field": "expires_at", "sortable": true},
          {"name": "updated_at", "align": "left", "label": "Updated At", "field": "updated_at", "sortable": true},
          {"name": "id", "align": "left", "label": "ID", "field": "id", "sortable": true}
        ],
        pagination: {
          sortBy: 'updated_at',
          rowsPerPage: 10,
          page: 1,
          descending: true,
          rowsNumber: 10
        }
      }
    }
  },
  watch: {
    'bunkersDataTable.search': {
      handler() {
        const props = {}
        if (this.bunkersDataTable.search) {
          props['search'] = this.bunkersDataTable.search
        }
        this.getBunkersData()
      }
    },
    'urlDataTable.search': {
      handler() {
        const props = {}
        if (this.urlDataTable.search) {
          props['search'] = this.urlDataTable.search
        }
        this.getUrlData()
      }
    },
    'urlDataFormDialog.bunkersData.value': {
      handler() {
        const props = {}
        if (this.urlDataTable.search) {
          props['search'] = this.urlDataTable.search
        }
        this.getUrlData()
      }
    },
    'signingRequestTable.search': {
      handler() {
        this.getSigningRequests()
      }
    }
  },

  methods: {

    //////////////// Bunkers Data ////////////////////////
    async showNewBunkersDataForm() {
      this.bunkersDataFormDialog.data = {
          name: null,
          nsec: null
      }
      this.bunkersDataFormDialog.show = true
    },
    async showEditBunkersDataForm(data) {
      this.bunkersDataFormDialog.data = {
        id: data.id,
        name: data.name,
        nsec: data.nsec
      }
      this.bunkersDataFormDialog.show = true
    },
    async saveBunkersData() {
      
      try {
        const data = {extra: {}, ...this.bunkersDataFormDialog.data}
        const method = data.id ? 'PUT' : 'POST'
        const entry = data.id ? `/${data.id}` : ''
        await LNbits.api.request(
          method,
          '/nostr_bunker/api/v1/bunkers_data' + entry,
          null,
          data
        )
        this.getBunkersData()
        this.bunkersDataFormDialog.show = false
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },

    async getBunkersData(props) {
      
      try {
        this.bunkersDataTable.loading = true
        const params = LNbits.utils.prepareFilterQuery(
          this.bunkersDataTable,
          props
        )
        const {data} = await LNbits.api.request(
          'GET',
          `/nostr_bunker/api/v1/bunkers_data/paginated?${params}`,
          null
        )
        this.bunkersDataList = data.data
        this.bunkersDataTable.pagination.rowsNumber = data.total
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      } finally {
        this.bunkersDataTable.loading = false
      }
    },
    async deleteBunkersData(bunkersDataId) {
      await LNbits.utils
        .confirmDialog('Are you sure you want to delete this Bunkers Data?')
        .onOk(async () => {
          try {
            
            await LNbits.api.request(
              'DELETE',
              '/nostr_bunker/api/v1/bunkers_data/' + bunkersDataId,
              null
            )
            await this.getBunkersData()
          } catch (error) {
            LNbits.utils.notifyApiError(error)
          }
        })
    },
    async exportBunkersDataCSV() {
      await LNbits.utils.exportCSV(
        this.bunkersDataTable.columns,
        this.bunkersDataList,
        'bunkers_data_' + new Date().toISOString().slice(0, 10) + '.csv'
      )
    },

    //////////////// Url Data ////////////////////////
    defaultUrlData() {
      return {
        name: null,
        capabilities: ['read_profile', 'read_follows', 'read_posts'],
        relays: [],
        permissions: ['get_public_key', 'ping'],
        auto_sign: false,
        confirm_sign: true,
        expires_at: null,
        can_read: true,
        can_write: false,
        post_rate_limit_per_day: null,
        secret: null
      }
    },
    inferCapabilitiesFromUrlData(data) {
      const permissions = data.permissions || []
      const capabilities = []

      if (data.can_read) {
        capabilities.push('read_posts')
        capabilities.push('read_profile')
        capabilities.push('read_follows')
      }
      if (permissions.includes('sign_event:0')) {
        capabilities.push('sign_profile')
      }
      if (permissions.includes('sign_event:3')) {
        capabilities.push('sign_follows')
      }
      if (permissions.includes('sign_event:1')) {
        capabilities.push('sign_posts')
      }
      if (permissions.includes('sign_event:5')) {
        capabilities.push('delete_posts')
      }
      if (permissions.includes('sign_event:6')) {
        capabilities.push('repost_posts')
      }
      if (permissions.includes('sign_event:7')) {
        capabilities.push('react_posts')
      }
      if (
        permissions.includes('nip04_decrypt') ||
        permissions.includes('nip44_decrypt')
      ) {
        capabilities.push('read_dms')
      }
      if (
        permissions.includes('sign_event:4') ||
        permissions.includes('sign_event:14') ||
        permissions.includes('sign_event:1059') ||
        permissions.includes('nip04_encrypt') ||
        permissions.includes('nip44_encrypt')
      ) {
        capabilities.push('sign_dms')
      }

      return capabilities
    },
    applyCapabilitiesToUrlData(data) {
      const capabilities = data.capabilities || []
      const managedPermissions = new Set([
        'get_public_key',
        'ping',
        'nip04_encrypt',
        'nip04_decrypt',
        'nip44_encrypt',
        'nip44_decrypt',
        'sign_event:0',
        'sign_event:1',
        'sign_event:3',
        'sign_event:4',
        'sign_event:5',
        'sign_event:6',
        'sign_event:7',
        'sign_event:14',
        'sign_event:1059'
      ])
      const permissions = new Set(
        (data.permissions || []).filter(permission => !managedPermissions.has(permission))
      )

      permissions.add('get_public_key')
      permissions.add('ping')

      if (capabilities.includes('sign_posts')) {
        permissions.add('sign_event:1')
      }
      if (capabilities.includes('sign_profile')) {
        permissions.add('sign_event:0')
      }
      if (capabilities.includes('sign_follows')) {
        permissions.add('sign_event:3')
      }
      if (capabilities.includes('delete_posts')) {
        permissions.add('sign_event:5')
      }
      if (capabilities.includes('repost_posts')) {
        permissions.add('sign_event:6')
      }
      if (capabilities.includes('react_posts')) {
        permissions.add('sign_event:7')
      }
      if (capabilities.includes('read_dms')) {
        permissions.add('nip04_decrypt')
        permissions.add('nip44_decrypt')
      }
      if (capabilities.includes('sign_dms')) {
        permissions.add('nip04_encrypt')
        permissions.add('nip44_encrypt')
        permissions.add('sign_event:4')
        permissions.add('sign_event:14')
        permissions.add('sign_event:1059')
      }

      return {
        ...data,
        permissions: Array.from(permissions),
        can_read: capabilities.some(capability =>
          ['read_profile', 'read_follows', 'read_posts', 'read_dms'].includes(capability)
        ),
        can_write: capabilities.some(capability =>
          [
            'sign_profile',
            'sign_follows',
            'sign_posts',
            'delete_posts',
            'repost_posts',
            'react_posts',
            'sign_dms'
          ].includes(capability)
        )
      }
    },
    async showNewUrlDataForm() {
      const bunker = this.bunkersDataList[0]
      this.urlDataFormDialog.bunkersData = bunker
        ? {label: bunker.name || bunker.id, value: bunker.id}
        : {label: 'All Bunkers Data', value: ''}
      this.urlDataFormDialog.data = this.defaultUrlData()
      this.urlDataFormDialog.show = true
    },
    async showEditUrlDataForm(data) {
      this.urlDataFormDialog.data = {
        ...this.defaultUrlData(),
        ...data,
        capabilities: this.inferCapabilitiesFromUrlData(data),
        relays: data.relays || [],
        permissions: data.permissions || []
      }
      this.urlDataFormDialog.show = true
    },
    async saveUrlData() {
      
      try {
        const data = this.applyCapabilitiesToUrlData({
          extra: {},
          ...this.urlDataFormDialog.data
        })
        const method = data.id ? 'PUT' : 'POST'
        const bunkerId = this.urlDataFormDialog.bunkersData.value
        const entry = data.id ? `/${data.id}` : `/${bunkerId}`
        await LNbits.api.request(
          method,
          '/nostr_bunker/api/v1/url_data' + entry,
          null,
          data
        )
        this.getUrlData()
        this.urlDataFormDialog.show = false
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },

    async getUrlData(props) {
      
      try {
        this.urlDataTable.loading = true
        let params = LNbits.utils.prepareFilterQuery(
          this.urlDataTable,
          props
        )
        const bunkersDataId = this.urlDataFormDialog.bunkersData.value
        if (bunkersDataId) {
          params += `&bunkers_data_id=${bunkersDataId}`
        }
        const {data} = await LNbits.api.request(
          'GET',
          `/nostr_bunker/api/v1/url_data/paginated?${params}`,
          null
        )
        this.urlDataList = data.data
        this.urlDataTable.pagination.rowsNumber = data.total
        await this.getSigningRequests()
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      } finally {
        this.urlDataTable.loading = false
      }
    },
    async deleteUrlData(urlDataId) {
      await LNbits.utils
        .confirmDialog('Are you sure you want to delete this Url Data?')
        .onOk(async () => {
          try {
            
            await LNbits.api.request(
              'DELETE',
              '/nostr_bunker/api/v1/url_data/' + urlDataId,
              null
            )
            await this.getUrlData()
          } catch (error) {
            LNbits.utils.notifyApiError(error)
          }
        })
    },

    async exportUrlDataCSV() {
      await LNbits.utils.exportCSV(
        this.urlDataTable.columns,
        this.urlDataList,
        'url_data_' + new Date().toISOString().slice(0, 10) + '.csv'
      )
    },
    async copyBunkerUrl(urlData) {
      if (!urlData.bunker_url) {
        LNbits.utils.notifyApiError(new Error('No bunker URL available for this record.'))
        return
      }
      await navigator.clipboard.writeText(urlData.bunker_url)
      Quasar.Notify.create({
        message: 'Bunker URL copied',
        color: 'positive',
        icon: 'content_copy'
      })
    },

    //////////////// Signing Requests ////////////////////////
    async getSigningRequests(props) {
      try {
        this.signingRequestTable.loading = true
        const params = LNbits.utils.prepareFilterQuery(
          this.signingRequestTable,
          props
        )
        const {data} = await LNbits.api.request(
          'GET',
          `/nostr_bunker/api/v1/signing_requests/paginated?${params}`,
          null
        )
        this.signingRequestList = data.data
        this.signingRequestTable.pagination.rowsNumber = data.total
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      } finally {
        this.signingRequestTable.loading = false
      }
    },
    async updateSigningRequest(signingRequest, status) {
      try {
        await LNbits.api.request(
          'PUT',
          '/nostr_bunker/api/v1/signing_requests/' + signingRequest.id,
          null,
          {status}
        )
        await this.getSigningRequests()
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    },

    //////////////// Utils ////////////////////////
    dateFromNow(date) {
      return moment(date).fromNow()
    },
    async fetchCurrencies() {
      try {
        const response = await LNbits.api.request('GET', '/api/v1/currencies')
        this.currencyOptions = ['sat', ...response.data]
      } catch (error) {
        LNbits.utils.notifyApiError(error)
      }
    }
  },
  ///////////////////////////////////////////////////
  //////LIFECYCLE FUNCTIONS RUNNING ON PAGE LOAD/////
  ///////////////////////////////////////////////////
  async created() {
    this.fetchCurrencies()
    this.getBunkersData()
    this.getUrlData()
    this.getSigningRequests()

    
    
  }
}

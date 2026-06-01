<template id="page-nostr_bunker">
  <div class="row q-col-gutter-md">
    <div class="col-12 col-md-8 col-lg-7 q-gutter-y-md">
    

      <div class="q-mt-lg">
        <span class="text-h5">Bunkers Data</span>
      </div>
      <q-card
        id="bunkersDataCard"
        class="q-mt-xs"
      >
        <q-card-section
          class=""
        >
          <div class="row items-center no-wrap q-mb-md">
            <div class="col">
              <q-input
                :label="$t('search')"
                dense
                class="q-pr-xl"
                v-model="bunkersDataTable.search"
              >
                <template v-slot:before>
                  <q-icon name="search"> </q-icon>
                </template>
                <template v-slot:append>
                  <q-icon
                    v-if="bunkersDataTable.search !== ''"
                    name="close"
                    @click="bunkersDataTable.search = ''"
                    class="cursor-pointer"
                  >
                  </q-icon>
                </template>
              </q-input>
            </div>
            <div class="col-auto">
              
              <q-btn
                @click="showNewBunkersDataForm()"
                unelevated
                split
                color="primary"
              >
                New Bunkers Data
              </q-btn>
              
              <q-btn
                flat
                color="grey"
                icon="file_download"
                @click="exportBunkersDataCSV"
                >CSV</q-btn
              >
            </div>
          </div>
          <q-table
            dense
            flat
            :rows="bunkersDataList"
            row-key="id"
            :columns="bunkersDataTable.columns"
            v-model:pagination="bunkersDataTable.pagination"
            :loading="bunkersDataTable.loading"
            @request="getBunkersData"
          >
            <template v-slot:header="props">
              <q-tr :props="props">
                <q-th auto-width></q-th>
                <q-th v-for="col in props.cols" :key="col.name" :props="props">
                  ${ col.label }
                </q-th>
              </q-tr>
            </template>

            <template v-slot:body="props">
              <q-tr :props="props">
                <q-td auto-width>
                   
                  <q-btn
                    flat
                    dense
                    size="xs"
                    @click="showEditBunkersDataForm(props.row)"
                    icon="edit"
                    color="light-blue"
                    class="q-mr-sm"
                  >
                    <q-tooltip> Edit </q-tooltip>
                  </q-btn>
                  
                  <q-btn
                    flat
                    dense
                    size="xs"
                    @click="deleteBunkersData(props.row.id)"
                    icon="cancel"
                    color="pink"
                    class="q-mr-sm"
                  >
                    <q-tooltip> Delete </q-tooltip>
                  </q-btn>
                </q-td>

                <q-td v-for="col in props.cols" :key="col.name" :props="props">
                  <div v-if="col.field == 'updated_at'">
                    <span v-text="dateFromNow(col.value)"> </span>
                  </div>
                  <div v-else>${ col.value }</div>
                </q-td>
              </q-tr>
            </template>
          </q-table>
        </q-card-section>
      </q-card>

      <div class="q-mt-lg">
        <span class="text-h5">Url Data</span>
      </div>
      <q-card
        id="urlDataCard"
        class="q-mt-xs"
      >
        <q-card-section
          class=""
        >
          <div class="row items-center no-wrap q-mb-md">
            <div class="col">
              <q-input
                :label="$t('search')"
                dense
                class="q-pr-xl"
                v-model="urlDataTable.search"
              >
                <template v-slot:before>
                  <q-icon name="search"> </q-icon>
                </template>
                <template v-slot:append>
                  <q-icon
                    v-if="urlDataTable.search !== ''"
                    name="close"
                    @click="urlDataTable.search = ''"
                    class="cursor-pointer"
                  >
                  </q-icon>
                </template>
              </q-input>
            </div>
            <div class="col-auto">
              <q-select
                filled
                dense
                v-model="urlDataFormDialog.bunkersData"
                :options="[
                  {label: 'All Bunkers Data', value: ''},
                  ...bunkersDataList.map(x => ({
                    label: x.name || x.id,
                    value: x.id
                  }))
                ]"
                label="Bunkers Data"
                class="q-mb-md"
              ></q-select>
            </div>
            <div class="col-auto">
              <q-btn
                @click="showNewUrlDataForm()"
                unelevated
                split
                color="primary"
                class="q-mb-md"
                :disable="bunkersDataList.length === 0"
              >
                New Url Data
              </q-btn>
            </div>
            <div class="col-auto">
              <q-btn
                flat
                color="grey"
                icon="file_download"
                class="q-mb-md"
                @click="exportUrlDataCSV"
                >CSV</q-btn
              >
            </div>
          </div>
          <q-table
            dense
            flat
            :rows="urlDataList"
            row-key="id"
            :columns="urlDataTable.columns"
            v-model:pagination="urlDataTable.pagination"
            :loading="urlDataTable.loading"
            @request="getUrlData"
          >
            <template v-slot:header="props">
              <q-tr :props="props">
                <q-th auto-width></q-th>
                <q-th v-for="col in props.cols" :key="col.name" :props="props">
                  ${ col.label }
                </q-th>
              </q-tr>
            </template>

            <template v-slot:body="props">
              <q-tr :props="props">
                <q-td auto-width>
                  <q-btn
                    flat
                    dense
                    size="xs"
                    @click="copyBunkerUrl(props.row)"
                    icon="content_copy"
                    color="primary"
                    class="q-mr-sm"
                  >
                    <q-tooltip> Copy bunker URL </q-tooltip>
                  </q-btn>
                  
                  <q-btn
                    flat
                    dense
                    size="xs"
                    @click="showEditUrlDataForm(props.row)"
                    icon="edit"
                    color="light-blue"
                    class="q-mr-sm"
                  >
                    <q-tooltip> Edit </q-tooltip>
                  </q-btn>
                  
                  <q-btn
                    flat
                    dense
                    size="xs"
                    @click="deleteUrlData(props.row.id)"
                    icon="cancel"
                    color="pink"
                    class="q-mr-sm"
                  >
                    <q-tooltip> Delete </q-tooltip>
                  </q-btn>
                </q-td>

                <q-td v-for="col in props.cols" :key="col.name" :props="props">
                  <div v-if="col.field == 'updated_at'">
                    <span v-text="dateFromNow(col.value)"> </span>
                  </div>
                  <div v-else>${ col.value }</div>
                </q-td>
              </q-tr>
            </template>
          </q-table>
        </q-card-section>
      </q-card>

      <div class="q-mt-lg">
        <span class="text-h5">Signing Requests</span>
      </div>
      <q-card id="signingRequestsCard" class="q-mt-xs">
        <q-card-section>
          <div class="row items-center no-wrap q-mb-md">
            <div class="col">
              <q-input
                :label="$t('search')"
                dense
                class="q-pr-xl"
                v-model="signingRequestTable.search"
              >
                <template v-slot:before>
                  <q-icon name="search"> </q-icon>
                </template>
              </q-input>
            </div>
          </div>
          <q-table
            dense
            flat
            :rows="signingRequestList"
            row-key="id"
            :columns="signingRequestTable.columns"
            v-model:pagination="signingRequestTable.pagination"
            :loading="signingRequestTable.loading"
            @request="getSigningRequests"
          >
            <template v-slot:body="props">
              <q-tr :props="props">
                <q-td auto-width>
                  <q-btn
                    flat
                    dense
                    size="xs"
                    @click="updateSigningRequest(props.row, 'approved')"
                    icon="check_circle"
                    color="green"
                    class="q-mr-sm"
                  >
                    <q-tooltip> Approve </q-tooltip>
                  </q-btn>
                  <q-btn
                    flat
                    dense
                    size="xs"
                    @click="updateSigningRequest(props.row, 'rejected')"
                    icon="cancel"
                    color="pink"
                    class="q-mr-sm"
                  >
                    <q-tooltip> Reject </q-tooltip>
                  </q-btn>
                </q-td>
                <q-td v-for="col in props.cols" :key="col.name" :props="props">
                  <div v-if="col.field == 'updated_at'">
                    <span v-text="dateFromNow(col.value)"> </span>
                  </div>
                  <div v-else>${ col.value }</div>
                </q-td>
              </q-tr>
            </template>
          </q-table>
        </q-card-section>
      </q-card>
    </div>
    
    <div class="col-12 col-md-4 col-lg-5 q-gutter-y-md">
      <q-card>
        <q-card-section>
          <h6 class="text-subtitle1 q-my-none">Nostr Bunker</h6>
          <p>Create & manage nostr urls</p>
        </q-card-section>
        <q-card-section class="q-pa-none">
          <q-separator></q-separator>
          <q-list>
            <!-- {% include "nostr_bunker/_api_docs.html" %} -->
            <q-separator></q-separator>
            <q-expansion-item group="extras" icon="info" label="More info">
              <q-card>
                <q-card-section>
                  <p>Some more info about Nostr Bunker.</p>
                  <small
                    >Created by
                    <a
                      class="text-secondary"
                      href="https://github.com/lnbits"
                      target="_blank"
                      >LNbits extension builder</a
                    >.</small
                  >
                </q-card-section>
              </q-card>
            </q-expansion-item>
          </q-list>
        </q-card-section>
      </q-card>
    </div>
    

    <!--/////////////////////////////////////////////////-->
    <!--//////////////FORM DIALOG////////////////////////-->
    <!--/////////////////////////////////////////////////-->


    <q-dialog v-model="bunkersDataFormDialog.show" position="top">
      <q-card
        v-if="bunkersDataFormDialog.show"
        class="q-pa-lg q-pt-md lnbits__dialog-card q-col-gutter-md"
      >
        <span class="text-h5">Bunkers Data</span>

       
<q-input
  filled
  dense
  v-model.trim="bunkersDataFormDialog.data.name"
  label="Name"
  hint="  (optional)"
></q-input>
  
<q-input
  filled
  dense
  v-model.trim="bunkersDataFormDialog.data.nsec"
  label="Nsec"
  hint="  (optional)"
></q-input>
 
        <div class="row q-mt-lg">
          <q-btn @click="saveBunkersData" unelevated color="primary">
            <span v-if="bunkersDataFormDialog.data.id">Update</span>
            <span v-else>Create</span>
          </q-btn>
          <q-btn v-close-popup flat color="grey" class="q-ml-auto"
            >Cancel</q-btn
          >
        </div>
      </q-card>
    </q-dialog>

    <q-dialog v-model="urlDataFormDialog.show" position="top">
      <q-card
        v-if="urlDataFormDialog.show"
        class="q-pa-lg q-pt-md lnbits__dialog-card q-col-gutter-md"
      >
        <span class="text-h5">Url Data</span>

       
<q-input
  filled
  dense
  v-model.trim="urlDataFormDialog.data.name"
  label="Name"
  hint="  (optional)"
></q-input>
<q-select
  v-if="!urlDataFormDialog.data.id"
  filled
  dense
  v-model="urlDataFormDialog.bunkersData"
  :options="bunkersDataList.map(x => ({label: x.name || x.id, value: x.id}))"
  label="Bunker"
></q-select>
<div class="text-subtitle2 q-mt-sm">Client capabilities</div>
<q-option-group
  v-model="urlDataFormDialog.data.capabilities"
  :options="capabilityOptions"
  type="checkbox"
  color="primary"
></q-option-group>
<div class="text-caption text-grey q-mt-xs q-mb-sm">
  Pick what this client should be able to do. The bunker will translate these into
  the underlying NIP-46 permissions automatically.
</div>
<q-select
  filled
  dense
  multiple
  use-input
  use-chips
  new-value-mode="add-unique"
  :options="relayOptions"
  v-model="urlDataFormDialog.data.relays"
  label="Relay URLs"
  hint="Required for the bunker:// invite URL"
></q-select>
<q-expansion-item
  dense
  dense-toggle
  icon="tune"
  label="Advanced NIP-46 permissions"
  class="q-mb-sm"
>
  <q-select
    filled
    dense
    multiple
    use-input
    use-chips
    new-value-mode="add-unique"
    :options="permissionOptions"
    v-model="urlDataFormDialog.data.permissions"
    label="Raw permissions"
    hint="Optional advanced override, for example sign_event:30023"
  ></q-select>
</q-expansion-item>
<q-input
  filled
  dense
  v-model.trim="urlDataFormDialog.data.secret"
  label="Secret"
  hint="Optional shared secret returned during connect"
></q-input>
<q-input
  filled
  dense
  type="datetime-local"
  v-model="urlDataFormDialog.data.expires_at"
  label="Expires at"
  hint="Optional expiration for this bunker URL"
></q-input>
<q-input
  filled
  dense
  type="number"
  min="0"
  v-model.number="urlDataFormDialog.data.post_rate_limit_per_day"
  label="Post rate limit per day"
  hint="Maximum write actions allowed per day"
></q-input>
<q-option-group
  v-model="urlDataFormDialog.data.signing_mode"
  :options="signingModeOptions"
  color="primary"
  inline
  dense
></q-option-group>
<div class="text-caption text-grey q-mt-xs">
  Read and write access are derived from the capabilities above. Auto sign approves
  matching sign requests immediately. Confirm sign puts them in the pending
  approval queue.
</div>
 
        <div class="row q-mt-lg">
          <q-btn @click="saveUrlData" unelevated color="primary">
            <span v-if="urlDataFormDialog.data.id">Update</span>
            <span v-else>Create</span>
          </q-btn>
          <q-btn v-close-popup flat color="grey" class="q-ml-auto"
            >Cancel</q-btn
          >
        </div>
      </q-card>
    </q-dialog>
  </div>
</template>

<template>
  <v-container fluid class="pa-4">
    <v-card>
      <v-card-title class="headline primary white--text">
        <v-icon left dark>mdi-clipboard-check-outline</v-icon>
        {{ __('Sales Status Tracker') }}
      </v-card-title>

      <!-- Filters Section -->
      <v-card-text>
        <v-row>
          <v-col cols="12" md="5">
            <v-text-field
              v-model="filters.customer_mobile"
              :label="__('Client Number')"
              prepend-icon="mdi-phone"
              clearable
              outlined
              dense
              @keyup.enter="searchInvoices"
            ></v-text-field>
          </v-col>

          <v-col cols="12" md="5">
            <v-text-field
              v-model="filters.invoice_id"
              :label="__('Invoice ID')"
              prepend-icon="mdi-file-document"
              clearable
              outlined
              dense
              @keyup.enter="searchInvoices"
            ></v-text-field>
          </v-col>

          <v-col cols="12" md="2">
            <v-btn
              color="primary"
              block
              large
              @click="searchInvoices"
              :loading="loading"
            >
              <v-icon left>mdi-magnify</v-icon>
              {{__("Search")}}
            </v-btn>
          </v-col>
        </v-row>

        <!-- Status Summary Cards -->
        <v-row class="mt-2" v-if="statusSummary.length > 0">
          <v-col
            v-for="stat in statusSummary"
            :key="stat.status"
            cols="6"
            sm="4"
            md="2"
          >
            <v-card
              outlined
              :color="getStatusColor(stat.status)"
              dark
              class="text-center pa-2"
            >
              <div class="text-h5 font-weight-bold">{{ stat.count }}</div>
              <div class="text-caption">{{ __(stat.status) || 'Not Set' }}</div>
            </v-card>
          </v-col>
        </v-row>
      </v-card-text>

      <!-- Results Table -->
      <v-card-text>
        <v-data-table
          :headers="headers"
          :items="invoices"
          :loading="loading"
          :items-per-page="10"
          class="elevation-1"
          :search="tableSearch"
        >
          <template v-slot:top>
            <v-toolbar flat>
              <v-toolbar-title>{{__("Invoices")}}</v-toolbar-title>
              <v-spacer></v-spacer>
              <v-text-field
                v-model="tableSearch"
                append-icon="mdi-magnify"
                :label="__('Search in results')"
                single-line
                hide-details
                dense
                outlined
                class="mr-2"
                style="max-width: 300px;"
              ></v-text-field>
              <v-btn
                color="primary"
                small
                @click="refreshSummary"
              >
                <v-icon small>mdi-refresh</v-icon>
              </v-btn>
            </v-toolbar>
          </template>

          <template v-slot:item.invoice_id="{ item }">
            <a :href="`/app/sales-invoice/${item.invoice_id}`" target="_blank">
              {{ item.invoice_id }}
            </a>
          </template>

          <template v-slot:item.posting_date="{ item }">
            {{ formatDate(item.posting_date) }}
          </template>

          <template v-slot:item.grand_total="{ item }">
            {{ formatCurrency(item.grand_total) }}
          </template>

          <template v-slot:item.pos_status="{ item }">
            <v-chip
              small
              :color="getStatusColor(item.pos_status)"
              dark
            >
              {{ __(item.pos_status) || 'Not Set' }}
            </v-chip>
          </template>

          <template v-slot:item.actions="{ item }">
            <v-menu :close-on-content-click="true">
              <template v-slot:activator="{ props }">
                <v-btn
                  size="small"
                  color="primary"
                  v-bind="props"
                >
                  Change Status
                  <v-icon end size="small">mdi-menu-down</v-icon>
                </v-btn>
              </template>
              <v-list density="compact">
                <v-list-item
                  v-for="status in statusOptions"
                  :key="status"
                  :value="status"
                  @click="updateStatus(item.invoice_id, status)"
                >
                  <v-list-item-title>{{ __(status) }}</v-list-item-title>
                </v-list-item>
              </v-list>
            </v-menu>
          </template>
        </v-data-table>
      </v-card-text>
    </v-card>
    <!-- Snackbar for notifications -->
    <v-snackbar
      v-model="snackbar.show"
      :color="snackbar.color"
      :timeout="3000"
      top
    >
      {{ snackbar.message }}
      <template v-slot:action="{ attrs }">
        <v-btn
          text
          v-bind="attrs"
          @click="snackbar.show = false"
        >
          Close
        </v-btn>
      </template>
    </v-snackbar>
  </v-container>
</template>

<script>
export default {
  name: 'StatusTracker',

  data() {
    return {
      filters: {
        customer_mobile: '',
        invoice_id: ''
      },
      invoices: [],
      statusSummary: [],
      loading: false,
      tableSearch: '',
      statusOptions: [
        'Received',
        'Delivered',
        'Ready',
        'Under Delivery',
        'Washing and Ironing'
      ],
      headers: [
        { title: __('Invoice ID'), value: 'invoice_id', sortable: true },
        { title: __('Customer'), value: 'customer_name', sortable: true },
        { title: __('Mobile'), value: 'customer_mobile', sortable: false },
        { title: __('Date'), value: 'posting_date', sortable: true },
        { title: __('Amount'), value: 'grand_total', sortable: true },
        { title: __('Status'), value: 'pos_status', sortable: true },
        { title: __('Actions'), value: 'actions', sortable: false, align: 'center' }
      ],
      snackbar: {
        show: false,
        message: '',
        color: 'success'
      }
    }
  },

  mounted() {
    this.loadStatusSummary();
  },

  methods: {
      testClick(item) {
    console.log('Button clicked!', item);
    alert('Button works!');
  },
      testMenu() {
    console.log('Menu ref:', this.$refs.statusMenu);
  },
    async searchInvoices() {
      if (!this.filters.customer_mobile && !this.filters.invoice_id) {
        this.showMessage('Please enter either Client Number or Invoice ID', 'warning');
        return;
      }

      this.loading = true;
      try {
        const response = await frappe.call({
          method: 'posawesome.posawesome.api.pos_status_tracker.get_sales_invoices',
          args: {
            filters: this.filters
          }
        });

        if (response.message.success) {
          this.invoices = response.message.data;
          if (this.invoices.length === 0) {
            this.showMessage('No invoices found', 'info');
          } else {
            this.showMessage(`Found ${this.invoices.length} invoice(s)`, 'success');
          }
        } else {
          this.showMessage(response.message.message || 'Error fetching invoices', 'error');
        }
      } catch (error) {
        console.error('Search error:', error);
        this.showMessage('Error searching invoices', 'error');
      } finally {
        this.loading = false;
      }
    },

    async updateStatus(invoiceId, newStatus) {
      try {
        const response = await frappe.call({
          method: 'posawesome.posawesome.api.pos_status_tracker.update_pos_status',
          args: {
            invoice_id: invoiceId,
            new_status: newStatus
          }
        });

        if (response.message.success) {
          // Update local data
          const invoice = this.invoices.find(inv => inv.invoice_id === invoiceId);
          if (invoice) {
            invoice.pos_status = newStatus;
          }
          this.showMessage('Status updated successfully', 'success');
          this.loadStatusSummary();
        } else {
          this.showMessage(response.message.message || 'Error updating status', 'error');
        }
      } catch (error) {
        console.error('Update error:', error);
        this.showMessage('Error updating status', 'error');
      }
    },

    async loadStatusSummary() {
      try {
        const response = await frappe.call({
          method: 'posawesome.posawesome.api.pos_status_tracker.get_status_summary'
        });

        if (response.message.success) {
          this.statusSummary = response.message.data;
        }
      } catch (error) {
        console.error('Summary error:', error);
      }
    },

    refreshSummary() {
      this.loadStatusSummary();
      this.showMessage('Summary refreshed', 'info');
    },

    getStatusColor(status) {
      const colors = {
        'Received': 'blue',
        'Delivered': 'green',
        'Ready': 'orange',
        'Under Delivery': 'purple',
        'Washing and Ironing': 'teal',
        'Not Set': 'grey'
      };
      return colors[status] || 'grey';
    },

    formatDate(date) {
      if (!date) return '';
      return new Date(date).toLocaleDateString();
    },

    formatCurrency(amount) {
      return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: frappe.defaults.get_default('currency') || 'USD'
      }).format(amount);
    },

    showMessage(message, color = 'info') {
      this.snackbar = {
        show: true,
        message: message,
        color: color
      };
    }
  }
}
</script>

<style scoped>
.v-data-table {
  font-size: 0.875rem;
}

a {
  text-decoration: none;
  color: #1976d2;
  font-weight: 500;
}

a:hover {
  text-decoration: underline;
}
</style>
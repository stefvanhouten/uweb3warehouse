(function () {
  'use strict';
  var tableEls = document.querySelectorAll('table.products');

  var productsTable = {
    el: null,
    tbodyEl: null,
    tfootEl: null,
    productTpl: null,
    vatTpl: null,
    vats: [],
    totalEx: 0,
    totalInc: 0,
    oldVats: [],

    create: function (tableEl) {
      var that = Object.create(this);

      that.el = tableEl;
      that.tbodyEl = that.el.tBodies[0];
      that.tfootEl = that.el.tFoot;
      that.resetInputs();
      that.productTpl = that.tbodyEl.querySelector('tr.product').cloneNode(true);
      that.vatTpl = that.tfootEl.querySelector('tr.vat').cloneNode(true);
      that.removeVatRows();
      that.tbodyEl.addEventListener('change', that.handleChange.bind(that));
    },

    resetInputs: function () {
      var inputEls = this.tbodyEl.getElementsByTagName('input');

      for (var i = 0; i < inputEls.length; i++) {
        inputEls[i].value = '';
      }
    },

    handleChange: function () {
      this.totalEx = 0;
      this.totalInc = 0;
      this.vats = [];
      for (var i = 0; i < this.tbodyEl.children.length; i++) {
        this.update(this.tbodyEl.children[i].querySelectorAll('input, output, select'));
      }
      if (this.isRowNeeded()) {
        let clone = this.productTpl.cloneNode(true);
        let inputs = clone.getElementsByTagName('input');
        for (let i = 0; i < inputs.length; ++i) {
          inputs[i].removeAttribute('required');
        }
        this.animate(this.tbodyEl.appendChild(clone));
      }
    },

    update: function (ioEls) {
      // TODO: No hardcoded apikey
      if(ioEls[0].value != ''){
          fetch(
            `/api/v1/search_product/${ioEls[0].value}?apikey=6435e79d8b1f6d9ef1cf35fd458bcd5e`
          )
            .then((response) => response.json())
            .then((data) => {
              ioEls[1].value = Number(data["cost"]) + Number(data["assemblycosts"]);
              ioEls[2].value = Number(data["vat"]);

              var price = ioEls[1].valueAsNumber;
              var vat = ioEls[2].valueAsNumber;
              let quantity = ioEls[3].valueAsNumber;
              var vatAmount = ((price * quantity)/ 100) * vat;
              var subtotal = (price * quantity) + vatAmount;

              if (!isNaN(vat) && !isNaN(vatAmount)) {
                if (!this.vats[vat]) {
                  this.vats[vat] = vatAmount;
                } else {
                  this.vats[vat] += vatAmount;
                }
                ioEls[4].value = "€ " + vatAmount.toFixed(2);
                ioEls[5].value = "€ " + subtotal.toFixed(2);
                this.totalEx += price * quantity;
                this.totalInc += subtotal;
              } else {
                ioEls[4].value = "";
                ioEls[5].value = "";
              }
              this.updateVatRows();
              this.tfootEl.querySelector("tr.totalex output").value =
                "€ " + this.totalEx.toFixed(2);
              this.tfootEl.querySelector("tr.totalinc output").value =
                "€ " + this.totalInc.toFixed(2);
            });
      }
    },

    updateVatRows: function () {
      var totalIncEl = this.tfootEl.querySelector('tr.totalinc');

      this.removeVatRows();
      this.vats.forEach(function (value, index) {
        var vatEl = this.vatTpl.cloneNode(true);

        vatEl.children[0].querySelector('output').value = index;
        vatEl.children[1].querySelector('output').value = '€ ' + value.toFixed(2);
        this.tfootEl.insertBefore(vatEl, totalIncEl);
        if (!this.oldVats[index]) {
          this.animate(vatEl, function () {
            this.oldVats[index] = value;
          }.bind(this));
        }
      }.bind(this));
    },

    removeVatRows: function () {
      var vatEls = this.tfootEl.querySelectorAll('tr.vat');

      for (var i = 0; i < vatEls.length; i++) {
        vatEls[i].parentNode.removeChild(vatEls[i]);
      }
    },

    isRowNeeded: function () {
      var rowEmpty = true,
        rowNeeded = true,
        inputEls;

      for (var i = 0; i < this.tbodyEl.children.length; i++) {
        inputEls = this.tbodyEl.children[i].getElementsByTagName('input');
        for (var j = 0; j < inputEls.length; j++) {
          if (inputEls[j].value !== '') {
            rowEmpty = false;
          }
        }
        if (rowEmpty) {
          rowNeeded = false;
        }
        rowEmpty = true;
      }
      return rowNeeded;
    },

    animate: function (rowEl, callback) {
      rowEl.classList.add('is-closed');
      for (var i = 0; i < rowEl.children.length; i++) {
        this.wrapInner(rowEl.children[i]);
      }
      window.requestAnimationFrame(function () {
        rowEl.classList.remove('is-closed');
        if (callback) {
          callback();
        }
      });
    },

    wrapInner: function (el) {
      var wrapper = document.createElement('div');

      while (el.firstChild) {
        wrapper.appendChild(el.firstChild);
      }
      el.appendChild(wrapper);
      return wrapper;
    },
  };


  for (var i = 0; i < tableEls.length; i++) {
    productsTable.create(tableEls[i]);
  }
})();

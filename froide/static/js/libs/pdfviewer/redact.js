function PDFRedact(pdfviewer) {
  this.pdfviewer = pdfviewer;

  this.canvas = document.createElement('canvas');
  this.canvas.width = pdfviewer.canvas.width;
  this.canvas.height = pdfviewer.canvas.height;
  this.canvas.className = 'pdf-redaction';
  this.pdfviewer.container.find('.pdf-canvas-container').append(this.canvas);
  this.ctx = this.canvas.getContext('2d');

  this.pageRedactions = {};
  this.currentPage = pdfviewer.currentPage;
  for (var i = 1; i <= pdfviewer.numPages; i += 1) {
    this.pageRedactions[i] = [];
  }
}

PDFRedact.prototype.setup = function(){
  var self = this;
  self.isDown = false;

  var getOffset = function(e){
    return [
      (e.offsetX || e.originalEvent.layerX),
      (e.offsetY || e.originalEvent.layerY)
    ];
  }

  $(this.canvas).on('mousedown', function(e) {
      self.isDown = true;
      var offset = getOffset(e);
      var x = offset[0];
      var y = offset[1];
      self.pageRedactions[self.currentPage].push([x, y, 0, 0]);
      self.drawRedaction();
  });

  $(this.canvas).on('mousemove', function(e) {
      if (!self.isDown) {
        return;
      }
      var redactions = self.pageRedactions[self.currentPage];
      var r = redactions[redactions.length - 1];
      var offset = getOffset(e);
      var x = offset[0];
      var y = offset[1];
      r[2] = x - r[0];
      r[3] = y - r[1];
      self.drawRedaction();
    });

  $(this.canvas).on('mouseup', function(e) {
    if (!self.isDown) {
      return;
    }
    var redactions = self.pageRedactions[self.currentPage];
    var r = redactions[redactions.length - 1];
    var offset = getOffset(e);
    var x = offset[0];
    var y = offset[1];
    r[2] = x - r[0];
    r[3] = y - r[1];
    self.isDown = false;
    self.drawRedaction();
  });

  this.pdfviewer.container.on('pageRendered', function(){
    self.canvas.width = self.pdfviewer.canvas.width;
    self.canvas.height = self.pdfviewer.canvas.height;
    self.currentPage = self.pdfviewer.currentPage;
    self.drawRedaction();
  });
};

PDFRedact.prototype.submitRedactions = function(form, progressbar){

  var self = this;

  self.canvas.style.display = 'none';

  var addKV = function(k,v){
    var inp = document.createElement('input');
    inp.type = 'hidden';
    inp.name = k;
    inp.value = v;
    form.append(inp);
  };
  var udpateProgress = function(pagenumber){
    if (!progressbar) {
      return;
    }
    progressbar.width(Math.round(pagenumber / self.pdfviewer.numPages * 100) + '%');
  };

  var extractImage = function(pagenumber) {
    self.applyRedaction(pagenumber, function(data){
      addKV('page_' + pagenumber, data);
      udpateProgress(pagenumber);
      if (pagenumber === self.pdfviewer.numPages) {
        form.submit();
      } else {
        extractImage(pagenumber + 1);
      }
    });
  };
  extractImage(1);
};

PDFRedact.prototype.applyRedaction = function(page, done){
  var self = this;
  self.pdfviewer.renderPage(page, function(){
    self.drawRedaction(page, self.pdfviewer.ctx);
    done(self.pdfviewer.canvas.toDataURL('image/png'));
  });
};

PDFRedact.prototype.drawRedaction = function(page, ctx){
  if (page === undefined) {
    page = this.pdfviewer.currentPage;
  }
  var redactions = this.pageRedactions[page];
  if (redactions === undefined) {
    return;
  }
  if (!ctx) {
    this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
  }
  ctx = ctx || this.ctx;
  ctx.fillStyle = '#000';
  for(var i = 0; i < redactions.length; i += 1) {
    ctx.fillRect(redactions[i][0], redactions[i][1], redactions[i][2], redactions[i][3]);
  }
};

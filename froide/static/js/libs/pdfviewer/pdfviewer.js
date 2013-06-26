
function SimplePDFViewer(containerId, pdfUrl){
  this.containerId = containerId;
  this.pdfUrl = pdfUrl;

  this.container = $('#' + containerId);

  this.prevButton = $('.pdf-prev', this.container);
  this.nextButton = $('.pdf-next', this.container);

  this.pdfTotal = $('.pdf-total', this.container);
  this.pdfCurrent = $('.pdf-current', this.container);

  this.canvas = $('.pdf-canvas', this.container)[0];
}

SimplePDFViewer.prototype.init = function(callback) {
  var self = this;

  PDFJS.getDocument(self.pdfUrl).then(function(pdf) {
    // Using promise to fetch the page
    self.pdf = pdf;
    self.currentPage = 1;
    self.numPages = pdf.pdfInfo.numPages;

    self.pdfTotal.text(self.numPages);
    self.pdfCurrent.text(self.currentPage);

    self.prevButton.on('click', function(){
      self.currentPage -= 1;
      if (self.currentPage < 1) {
        self.currentPage = 1;
      }
      self.updateButtons();
      self.renderPage(self.currentPage);
      self.pdfCurrent.text(self.currentPage);
    });

    self.nextButton.on('click', function(){
      self.currentPage += 1;
      if (self.currentPage > self.numPages) {
        self.currentPage = self.numPages;
      }
      self.updateButtons();
      self.renderPage(self.currentPage);
      self.pdfCurrent.text(self.currentPage);
    });

    self.updateButtons();

    if (callback){
      callback();
    }

  });

};

SimplePDFViewer.prototype.updateButtons = function(){
  var self = this;
  if (self.currentPage == 1) {
    self.prevButton.prop('disabled', true);
  } else {
    self.prevButton.prop('disabled', false);
  }
  if (self.currentPage == self.numPages) {
    self.nextButton.prop('disabled', true);
  } else {
    self.nextButton.prop('disabled', false);
  }
};

SimplePDFViewer.prototype.renderPage = function(pageno, callback) {
  var self = this;

  if (pageno === undefined) {
    pageno = self.currentPage;
  }

  self.pdf.getPage(pageno).then(function(page) {
    var scale = 1.5;
    var viewport = page.getViewport(scale);

    //
    // Prepare canvas using PDF page dimensions
    //
    self.ctx = self.canvas.getContext('2d');
    self.canvas.height = viewport.height;
    self.canvas.width = viewport.width;

    //
    // Render PDF page into canvas context
    //
    var renderContext = {
      canvasContext: self.ctx,
      viewport: viewport
    };
    page.render(renderContext).then(function(){
      if (callback){
        callback();
      }

      self.container.trigger('pageRendered');

    });

  });
};

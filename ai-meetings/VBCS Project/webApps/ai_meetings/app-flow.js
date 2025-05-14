define([], () => {
  'use strict';

  class AppModule {
  }

      
     AppModule.prototype.isFormValid = function(form) {
    var tracker = document.getElementById(form); 
    if (tracker.valid === "valid") {
        return true;
    } else {
        tracker.showMessages();
        tracker.focusOn("@firstInvalidShown");
        return false;
    }
  };
  
  return AppModule;
});

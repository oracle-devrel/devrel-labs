define([
  'vb/action/actionChain',
  'vb/action/actions',
  'vb/action/actionUtils',
], (
  ActionChain,
  Actions,
  ActionUtils
) => {
  'use strict';

  class checkWidth extends ActionChain {

    /**
     * @param {Object} context
     * @return {{cancelled:boolean}}
     */
    async run(context) {
      const { $page, $flow, $application } = context;

      if ($application.responsive.mdUp) {
        $page.variables.width = 220;
        $page.variables.widthSpeakers = 140;
        $page.variables.widthCreation = 240;
      } else if ($application.responsive.smOnly) {
        $page.variables.width = 85;
        $page.variables.widthSpeakers = 110;
        $page.variables.widthCreation = 120;
      }
    }
  }

  return checkWidth;
});

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

  class ButtonActionRefresh extends ActionChain {

    /**
     * @param {Object} context
     */
    async run(context) {
      const { $page, $flow, $application } = context;
      window.location.href = window.location.href;//(window.location.href.indexOf('?') > -1 ? '&' : '?') + 'meetingID='+$page.variables.meetingID;
    }
  }

  return ButtonActionRefresh;
});

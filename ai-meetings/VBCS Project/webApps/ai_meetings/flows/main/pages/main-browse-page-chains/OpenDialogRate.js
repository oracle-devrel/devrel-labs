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

  class OpenDialogRate extends ActionChain {

    /**
     * @param {Object} context
     */
    async run(context) {
      const { $page, $flow, $application } = context;

      const callComponentMethodOjDialogRateOpenResult = await Actions.callComponentMethod(context, {
        selector: '#oj-dialog--rate',
        method: 'open',
      });
    }
  }

  return OpenDialogRate;
});

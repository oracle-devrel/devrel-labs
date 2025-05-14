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

  class ClickGear extends ActionChain {

    /**
     * @param {Object} context
     */
    async run(context) {
      const { $page, $flow, $application } = context;

      const callComponentMethodOjDialogConfigurationOpenResult = await Actions.callComponentMethod(context, {
        selector: '#oj-dialog--configuration',
        method: 'open',
      });
    }
  }

  return ClickGear;
});

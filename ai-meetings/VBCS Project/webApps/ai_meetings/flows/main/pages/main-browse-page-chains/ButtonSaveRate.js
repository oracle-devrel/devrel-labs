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

  class ButtonSaveRate extends ActionChain {

    /**
     * @param {Object} context
     */
    async run(context) {
      const { $page, $flow, $application } = context;

      const callRestBusinessObjectsCreateRateResult = await Actions.callRest(context, {
        endpoint: 'businessObjects/create_Rate',
        body: {
      "feedback": $page.variables.feedback,
      "rate": $page.variables.rate,
      },
      });


      const callComponentMethodOjDialogRateCloseResult = await Actions.callComponentMethod(context, {
        selector: '#oj-dialog--rate',
        method: 'close',
      });
    }
  }

  return ButtonSaveRate;
});

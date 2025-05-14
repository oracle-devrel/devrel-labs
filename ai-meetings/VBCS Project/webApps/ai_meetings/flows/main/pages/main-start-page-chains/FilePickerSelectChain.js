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

  class FilePickerSelectChain extends ActionChain {

    /**
     * @param {Object} context
     * @param {Object} params
     * @param {object[]} params.files 
     */
    async run(context, { files }) {
      const { $page, $flow, $application } = context;

      $page.variables.loading = true;
      let size="";
      if(files[0].size === 0) size= '0 Bytes';
      var k = 1000,
        dm = 2,
        sizes = ['Bytes', 'KB', 'MB', 'GB','TB', 'PB', 'EB', 'ZB', 'YB'],
        i = Math.floor(Math.log(files[0].size) / Math.log(k));
      size= parseFloat((files[0].size / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
      $page.variables.fileSize = size;

    
      function obtenerExtension(nombreArchivo) {
          if (typeof nombreArchivo !== 'string' || !nombreArchivo) {
              return ''; // Retorna una cadena vacía si el input no es válido
          }
          const ultimoPunto = nombreArchivo.lastIndexOf(".");
          if (ultimoPunto === -1) return ''; // Retorna una cadena vacía si no hay un punto en el nombre del archivo
          return nombreArchivo.slice(ultimoPunto + 1);
      }

      function generateUUID() {
          let dt = new Date().getTime();
          const uuid = 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
              const r = (dt + Math.random()*16)%16 | 0;
              dt = Math.floor(dt/16);
              return (c == 'x' ? r : (r&0x3|0x8)).toString(16);
          });
          return uuid;
      }

    let uuid = generateUUID();

    let ext = obtenerExtension(files[0].name);
    $page.variables.filename =  uuid+"."+ext;


      const callRestStoragePutObjectResult = await Actions.callRest(context, {
        endpoint: 'Storage/putObject',
        uriParams: {
          'object_name': $page.variables.filename,
          bucket: $application.variables.bucketName,
          'object_storage_namespace': $application.variables.namespace,
        },
        body: files[0],
      });

      if (callRestStoragePutObjectResult.status===200) {

        $page.variables.uploadSuccess = true;
      } else {
        await Actions.fireNotificationEvent(context, {
          summary: 'There was an error uploading the file',
          displayMode: 'transient',
          type: 'error',
        });
      }

      $page.variables.loading = false;

      return;
    }
  }

  return FilePickerSelectChain;
});

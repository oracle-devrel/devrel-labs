import { h } from "preact";
import { useState } from "preact/hooks";
import { ResultsView } from "./VisionAIResultView";
import { ObjectStorageForm } from "./ObjectStorageForm";
type attr = {
  bucketName?: string | undefined;
  selectImage?: string| undefined;
  regionName?: string| undefined;
};
type Props = {
  onActivityChanged: (event: any) => void;
};

export function ParentContainer(){
const [formData, setFormData] = useState<attr | null>({
  });
  const activityChangedHandler = (data: any) => {
    setFormData(data);
  };
return (
    <div id="parentContainer" class="oj-flex oj-flex-init parent-container parent-container-margin" >
      <div class="separator-line"></div>
     <ObjectStorageForm  onActivityChanged={activityChangedHandler}/>
     {formData && <ResultsView  activity={formData} />}
    
    </div>
  );
};

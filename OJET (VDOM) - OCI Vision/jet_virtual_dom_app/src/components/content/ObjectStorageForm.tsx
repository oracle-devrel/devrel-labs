import { h, ComponentProps } from "preact";
import { useState, useRef} from "preact/hooks";
import MutableArrayDataProvider = require("ojs/ojmutablearraydataprovider");
import "ojs/ojbutton";
import "ojs/ojcheckboxset";
import "ojs/ojformlayout";
import "ojs/ojinputtext";
import "ojs/ojdatetimepicker";
import "ojs/ojselectsingle";
import "ojs/ojdialog";
import "ojs/ojprogress-bar";
import { ojButton } from "ojs/ojbutton";
import { ojDialog } from "ojs/ojdialog";
import { ojSelectSingle } from "ojs/ojselectsingle";


type Props = {
  onActivityChanged: (event: any) => void;
};
const images: Array<object> = [];

type ImageObjectList = {
  id: number;
  value: string;
  label: string;
};

type EnvirmentDetails = {
  id: number;
  name: string;
  title: string;
  imageUrl: string;
};
let serviceUrl =
  "http://localhost:8080/ai/vision/objectlist?"

type InputTextProps = ComponentProps<"oj-input-text">;

type FormLayoutProps = ComponentProps<"oj-form-layout">;

const hintDefinition: InputTextProps["helpHints"] = {
  definition: "Enter Bucket Name",
};
const placeholder: InputTextProps["placeholder"] = "Enter Bucket Name";
const lblHint: InputTextProps["labelHint"] = "Bucket Name";

let value: string = "Your Bucket Name";
let name: string = "Your Region";

export function ObjectStorageForm(props: Props){
  const imageData = useRef(
    new MutableArrayDataProvider<ImageObjectList["value"], ImageObjectList>([{ id: 1, value: "All", label: "All" }], {
      keyAttributes: "value" ,
    })
  );  
  const [formData, setFormData] = useState({
    regionName: name,
    selectImage: "",
    bucketName: value,
  });

  const [isDisabled, setIsDisabled] = useState(true);
  const [isBucketNameDisabled, setIsBucketNameDisabled] = useState(true);
  const [isSelectImageDisabled, setIsSelectImageDisabled] = useState(true);
  const [density, setDensity] =
    useState<FormLayoutProps["userAssistanceDensity"]>("efficient");
   const [imageUrl, setImageUrl] = useState<any>("");
  const dialogRef = useRef<ojDialog>(null);
  const bucketNameValuechange = (event:any) =>{
    const newValue = event.detail.value;
    if(newValue){
    setFormData(prevState => ({
        ...prevState,
        bucketName: newValue
    }));

    serviceUrl = serviceUrl+`bucket=${event.detail.value}&region=${formData.regionName}`;
    fetch(serviceUrl)
    .then((response) => response.json())
    .then((result) => {
        const lovData = result.map((item:EnvirmentDetails) => ({
            id: item.id,
            value: item.imageUrl,
            label: item.name,
        }));
        imageData.current.data = lovData;
        setIsSelectImageDisabled(false);
    })
    .catch((error) => {
        event.preventDefault();
        dialogRef.current!.open();
    });
  }
  }
  const regionChange=(event:any)=>{
    if(event.detail.value){
    setIsBucketNameDisabled(false);
    setFormData(prevState => ({
      ...prevState,
      regionName: event.detail.value
  }));
}else{
  setIsBucketNameDisabled(true);
  setIsSelectImageDisabled(true);
  setFormData(prevState => ({
    ...prevState,
    bucketName: value,
    selectImage:""
}));
}
  };

  const onChange = (event: any) => {
    const { id, value } = event.currentTarget;
    if(id && value && id =="selectImage"){
      setImageUrl(value);
     setIsDisabled(false);
    }else{
      setIsDisabled(true);
    }
    setFormData({
      ...formData,
      [event.currentTarget.id]: event.detail.value,
    });
   
  }
  const onSubmit = async (event: ojButton.ojAction) => {
    try {
      await props.onActivityChanged(formData); 
    } catch (error) {
      console.error("Error:", error);
      dialogRef.current!.open(); 
    }
  };

  const close = () => {
    dialogRef.current!.close();
  };

  return (
    <div class="oj-flex-item oj-md-6">
       <div class="oj-typography-subheading-md">Object Storage Details</div>
      <oj-form-layout
        userAssistanceDensity={density}
        labelEdge="inside"
        columns={1}
        class="oj-md-margin-4x-horizontal">
        <oj-input-text
          id="regionName"
          value={formData.regionName}
          labelHint="Region"
          onvalueChanged={regionChange}>
        </oj-input-text>
        <oj-input-text
          id="bucketName"
          value={formData.bucketName}
          placeholder={placeholder}
          labelHint={lblHint}
          helpHints={hintDefinition}
          disabled={isBucketNameDisabled}
          onvalueChanged={bucketNameValuechange}
         ></oj-input-text>
        <oj-select-single
          id="selectImage"
          labelHint="Select Image Object"
          data={imageData.current}
          value={formData.selectImage}
          disabled={isSelectImageDisabled}
          onvalueChanged={onChange}></oj-select-single>
          {!isDisabled && (
         <img src={imageUrl} alt="placeholder" width={450}/>
           )}
        <oj-button onojAction={onSubmit} disabled={isDisabled}>
         Submit
        </oj-button>
      </oj-form-layout>
      
      <oj-dialog ref={dialogRef} dialogTitle="Error">
        <div slot="body">
                <span>
                 Please provide correct Bucket Name
                </span>
          <div>
        </div>
        </div>
        <div slot="footer">
          <oj-button id="okButton" onojAction={close}>
            OK
          </oj-button>
        </div>
      </oj-dialog>
    </div>
  );
}

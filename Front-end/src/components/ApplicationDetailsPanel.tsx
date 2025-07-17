import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Application } from "@/types/application";
import { useComments } from "@/hooks/useComments";
import { useAuditLogs } from "@/hooks/useAuditLogs";
import { useCallingLogs } from "@/hooks/useCallingLogs";
// import { useRealtimeUpdates } from "@/hooks/useRealtimeUpdates";
import { useAuth } from "@/hooks/useAuth";
import { toast } from "sonner";
import ApplicationHeader from "./details/ApplicationHeader";
import ContactsTab from "./details/ContactsTab";
import StatusTab from "./details/StatusTab";
import CommentsTab from "./details/CommentsTab";
import DetailsTab from "./details/DetailsTab";
import { useApplicationHandlers } from "./details/ApplicationHandlers";
import { useEffect, useState, useCallback, useRef } from "react";
import { useRepaymentHistory } from "@/hooks/useRepaymentHistory";
// import { supabase } from '@/integrations/api/client'; // REMOVE THIS
import { useMonthlyApplicationData } from '@/hooks/useMonthlyApplicationData';
import MonthSelector from './details/MonthSelector';
import { formatEmiMonth } from "@/utils/formatters";
import { monthToEmiDate } from "@/utils/dateUtils";
import { getApplicationDetails } from '@/integrations/api/client';

interface ApplicationDetailsPanelProps {
  application: Application | null;
  onClose: () => void;
  onSave: (updatedApp: Application) => void;
  onDataChanged?: () => void;
  selectedEmiMonth?: string | null;
  refetchStatusCounts?: () => void;
}

const ApplicationDetailsPanel = ({ 
  application, 
  onClose, 
  onSave, 
  onDataChanged, 
  selectedEmiMonth,
  refetchStatusCounts
}: ApplicationDetailsPanelProps) => {
  const { user } = useAuth();
  const [currentApplication, setCurrentApplication] = useState<Application | null>(application);
  const [selectedMonth, setSelectedMonth] = useState<string>('');
  const [monthSpecificPtpDate, setMonthSpecificPtpDate] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>('contacts');
  
  // Add tracking for user-initiated month changes
  const userSelectedMonthRef = useRef<boolean>(false);
  const isUpdatingStatusRef = useRef<boolean>(false);
  const initializedRef = useRef<boolean>(false);
  
  const { monthlyData, availableMonths, availableMonthsFormatted, loading: monthlyLoading, getApplicationForMonth } = useMonthlyApplicationData(currentApplication?.applicant_id);

  // Handle application changes
  useEffect(() => {
    console.log('ApplicationDetailsPanel: Application changed', application?.applicant_id);
    setCurrentApplication(application);
    // Reset initialization flag when application changes
    initializedRef.current = false;
    userSelectedMonthRef.current = false;
    // Clear selectedMonth when application changes to force proper initialization
    setSelectedMonth('');
  }, [application]);
  
  const { repaymentHistory } = useRepaymentHistory(currentApplication?.applicant_id);
  
  // Initialize comments hook but only fetch when needed
  const { comments, fetchComments, addComment, clearComments } = useComments(selectedMonth);
  
  const { auditLogs, addAuditLog, refetch: refetchAuditLogs } = useAuditLogs(currentApplication?.applicant_id, selectedMonth);
  const { callingLogs, addCallingLog, refetch: refetchCallingLogs } = useCallingLogs(currentApplication?.applicant_id, selectedMonth);

  // Fetch month-specific PTP date (DISABLED)
  useEffect(() => {
    setMonthSpecificPtpDate(null); // Feature disabled until real API is available
  }, [currentApplication?.applicant_id, selectedMonth]);

  // Clear comments when application changes
  useEffect(() => {
    console.log('ApplicationDetailsPanel: Clearing comments for application', currentApplication?.applicant_id);
    clearComments();
  }, [currentApplication?.applicant_id, clearComments]);

  // Improved month initialization logic with user selection tracking
  useEffect(() => {
    console.log('ApplicationDetailsPanel: Month initialization check', {
      selectedEmiMonth,
      availableMonths,
      currentApplicationId: currentApplication?.applicant_id,
      selectedMonth,
      applicationDemandDate: currentApplication?.demand_date,
      userSelectedMonth: userSelectedMonthRef.current,
      isUpdatingStatus: isUpdatingStatusRef.current,
      initialized: initializedRef.current
    });
    
    // Don't reinitialize if:
    // 1. Already initialized and user has made a selection OR already has a selected month
    // 2. Currently updating status (prevents interference)
    // 3. No available months or application
    // 4. User has explicitly selected a month (preserve their choice)
    if ((initializedRef.current && (userSelectedMonthRef.current || selectedMonth)) || 
        isUpdatingStatusRef.current || 
        availableMonths.length === 0 || 
        !currentApplication?.applicant_id ||
        (userSelectedMonthRef.current && selectedMonth)) {
      return;
    }
    
    // Only initialize if we don't have a selected month yet
    if (!selectedMonth) {
      let initialMonth = '';
      
      // Priority 1: Try selectedEmiMonth from filters first (user's current context)
      if (selectedEmiMonth) {
        const matchingMonth = availableMonths.find(month => 
          formatEmiMonth(month) === selectedEmiMonth
        );
        
        if (matchingMonth) {
          initialMonth = matchingMonth;
          console.log('ApplicationDetailsPanel: Found matching month for selectedEmiMonth', selectedEmiMonth, '->', initialMonth);
        } else {
          // If no exact match found, try to find a month that's close
          const normalizedSelectedMonth = selectedEmiMonth.toLowerCase().replace(/\s+/g, '');
          const closeMatch = availableMonths.find(month => {
            const normalizedMonth = formatEmiMonth(month).toLowerCase().replace(/\s+/g, '');
            return normalizedMonth === normalizedSelectedMonth;
          });
          
          if (closeMatch) {
            initialMonth = closeMatch;
            console.log('ApplicationDetailsPanel: Found close match for selectedEmiMonth', selectedEmiMonth, '->', initialMonth);
          }
        }
      }
      
      // Priority 2: Try to match the application's own demand_date
      if (!initialMonth && currentApplication?.demand_date) {
        const applicationMonth = availableMonths.find(month => 
          month === currentApplication.demand_date
        );
        
        if (applicationMonth) {
          initialMonth = applicationMonth;
          console.log('ApplicationDetailsPanel: Found matching month for application demand_date', currentApplication.demand_date, '->', initialMonth);
        } else {
          // If exact match not found, try formatted match
          const applicationMonthFormatted = formatEmiMonth(currentApplication.demand_date);
          const formattedMatch = availableMonths.find(month => 
            formatEmiMonth(month) === applicationMonthFormatted
          );
          
          if (formattedMatch) {
            initialMonth = formattedMatch;
            console.log('ApplicationDetailsPanel: Found formatted match for application demand_date', applicationMonthFormatted, '->', initialMonth);
          }
        }
      }
      
      // Priority 3: Fallback to most recent month
      if (!initialMonth) {
        initialMonth = availableMonths[availableMonths.length - 1];
        console.log('ApplicationDetailsPanel: No match found, using most recent month', initialMonth);
      }
      
      console.log('ApplicationDetailsPanel: Setting initial month to', initialMonth);
      setSelectedMonth(initialMonth);
      initializedRef.current = true;
      // This is automatic initialization, not user-initiated
      userSelectedMonthRef.current = false;
    }
  }, [availableMonths, selectedMonth, currentApplication?.applicant_id, currentApplication?.demand_date, selectedEmiMonth]);

  // Handle user-initiated month changes
  const handleMonthChange = useCallback((newMonth: string) => {
    console.log('ApplicationDetailsPanel: User changed month to', newMonth);
    setSelectedMonth(newMonth);
    userSelectedMonthRef.current = true; // Mark as user-initiated
  }, []);

  // Only fetch comments when the comments tab is active AND we have the required data
  const handleCommentsTabAccess = useCallback(async () => {
    if (currentApplication?.applicant_id && selectedMonth) {
      console.log('ApplicationDetailsPanel: Fetching comments for active tab', {
        applicationId: currentApplication.applicant_id,
        selectedMonth
      });
      try {
        await fetchComments(currentApplication.applicant_id);
      } catch (error) {
        console.error('Error fetching comments:', error);
      }
    }
  }, [currentApplication?.applicant_id, selectedMonth, fetchComments]);

  // Handle tab changes
  const handleTabChange = useCallback((value: string) => {
    setActiveTab(value);
    if (value === 'comments') {
      handleCommentsTabAccess();
    }
  }, [handleCommentsTabAccess]);

  const monthlyCollectionData = selectedMonth ? getApplicationForMonth(selectedMonth) : null;

  // Enhanced real-time updates with status update tracking
  // Comment out the real-time updates hook to prevent supabase.channel error
  // useRealtimeUpdates({
  //   onCallingLogUpdate: async () => { 
  //     refetchCallingLogs(); 
  //     if (!isUpdatingStatusRef.current) {
  //       await onDataChanged?.(); 
  //     }
  //   },
  //   onAuditLogUpdate: async () => { 
  //     refetchAuditLogs(); 
  //     if (!isUpdatingStatusRef.current) {
  //       await onDataChanged?.(); 
  //     }
  //   },
  //   onCommentUpdate: async () => { 
  //     if (currentApplication?.applicant_id && activeTab === 'comments') {
  //       await handleCommentsTabAccess();
  //     }
  //     if (!isUpdatingStatusRef.current) {
  //       await onDataChanged?.(); 
  //     }
  //   },
  //   onApplicationUpdate: async () => {
  //     // When application data changes from real-time, update both local state and parent
  //     if (currentApplication?.applicant_id && !isUpdatingStatusRef.current) {
  //       // Fetch the latest application data from real backend
  //       getApplicationDetails(currentApplication.applicant_id)
  //         .then((data) => {
  //           if (data) {
  //             const updatedApp = { ...currentApplication, ...data };
  //             setCurrentApplication(updatedApp);
  //             onSave(updatedApp);
  //           }
  //         })
  //         .catch((error) => {
  //           console.error('Failed to fetch application details:', error);
  //         });
  //     }
  //     if (!isUpdatingStatusRef.current) {
  //       await onDataChanged?.();
  //     }
  //   },
  //   onPtpDateUpdate: async () => { 
  //     refetchAuditLogs(); 
  //     // Feature disabled until real API is available
  //     setMonthSpecificPtpDate(null);
  //     if (!isUpdatingStatusRef.current) {
  //       await onDataChanged?.(); 
  //     }
  //   }
  // });

  const {
    handleStatusChange,
    handlePtpDateChange,
    handleCallingStatusChange
  } = useApplicationHandlers(currentApplication, user, addAuditLog, addCallingLog, (updatedApp) => {
    setCurrentApplication(updatedApp);
    onSave(updatedApp);
    onDataChanged?.();
  }, selectedMonth);

  // Enhanced status change handler with update tracking
  const handleStatusChangeWithTracking = useCallback(async (newStatus: string) => {
    isUpdatingStatusRef.current = true;
    try {
      await handleStatusChange(newStatus);
    } finally {
      // Reset the flag after a delay to allow for real-time updates to settle
      setTimeout(() => {
        isUpdatingStatusRef.current = false;
      }, 1000);
    }
  }, [handleStatusChange]);

  // Enhanced PTP date change handler with update tracking
  const handlePtpDateChangeWithTracking = useCallback(async (newDate: string) => {
    isUpdatingStatusRef.current = true;
    // Mark that user has selected a month to prevent reinitialization
    userSelectedMonthRef.current = true;
    try {
      await handlePtpDateChange(newDate);
    } finally {
      // Reset the flag after a delay to allow for real-time updates to settle
      setTimeout(() => {
        isUpdatingStatusRef.current = false;
      }, 1000);
    }
  }, [handlePtpDateChange]);

  const displayApplication = (() => {
    if (!currentApplication) return null;
    if (monthlyCollectionData) {
      return {
        ...currentApplication,
        team_lead: monthlyCollectionData.team_lead || currentApplication.team_lead,
        rm_name: monthlyCollectionData.rm_name || currentApplication.rm_name,
        repayment: monthlyCollectionData.repayment || currentApplication.repayment,
        emi_amount: monthlyCollectionData.emi_amount || currentApplication.emi_amount,
        last_month_bounce: monthlyCollectionData.last_month_bounce || currentApplication.last_month_bounce,
        lms_status: monthlyCollectionData.lms_status || currentApplication.lms_status,
        collection_rm: monthlyCollectionData.collection_rm || currentApplication.collection_rm,
        demand_date: monthlyCollectionData.demand_date || currentApplication.demand_date,
        amount_collected: monthlyCollectionData.amount_collected || currentApplication.amount_collected,
        ptp_date: monthSpecificPtpDate || currentApplication.ptp_date,
        vehicle_status: currentApplication.vehicle_status,
      };
    }
    return {
      ...currentApplication,
      ptp_date: monthSpecificPtpDate || currentApplication.ptp_date,
      vehicle_status: currentApplication.vehicle_status,
    };
  })();

  if (!currentApplication) return null;

  const handleAddComment = async (content: string) => {
    if (currentApplication?.applicant_id) {
      try {
        await addComment(currentApplication.applicant_id, content, selectedMonth);
        toast.success('Comment added');
        // Force refresh comments after adding
        await fetchComments(currentApplication.applicant_id);
        await onDataChanged?.();
      } catch (error) {
        console.error('Error adding comment:', error);
        toast.error('Failed to add comment');
      }
    }
  };

  // Disable handleVehicleStatusChange
  const handleVehicleStatusChange = async (newStatus: string) => {
    toast.error('Vehicle status update not available in this mode.');
  };

  return (
    <div className="application-details-panel bg-white flex flex-col">
      <div className="flex-shrink-0 p-4 sm:p-6 border-b bg-white">
        <div className="flex items-center justify-between mb-3 sm:mb-6">
          <h2 className="text-lg sm:text-xl font-semibold">Application Details</h2>
          <Button variant="ghost" size="sm" onClick={onClose} className="hover:bg-gray-100 rounded-full h-8 w-8 p-0">
            <X className="h-4 w-4" />
          </Button>
        </div>
        <ApplicationHeader application={displayApplication} />
      </div>

      <MonthSelector
        availableMonths={availableMonths}
        availableMonthsFormatted={availableMonthsFormatted}
        selectedMonth={selectedMonth}
        onMonthChange={handleMonthChange}
        loading={monthlyLoading}
      />

      <div className="flex-1 flex-col-min-h-0">
        <Tabs value={activeTab} onValueChange={handleTabChange} className="h-full flex flex-col">
          <div className="flex-shrink-0 pt-3 sm:pt-4 border-b">
            <TabsList className="grid w-full grid-cols-4 text-xs sm:text-sm h-auto">
              <TabsTrigger value="contacts" className="py-2">Contacts</TabsTrigger>
              <TabsTrigger value="status" className="py-2">Status</TabsTrigger>
              <TabsTrigger value="comments" className="py-2">Comments</TabsTrigger>
              <TabsTrigger value="details" className="py-2">Details</TabsTrigger>
            </TabsList>
          </div>
          
          <div className="application-details-content flex-1 overflow-y-auto p-4 sm:p-4">
            <TabsContent value="contacts" className="m-0">
              <ContactsTab 
                application={currentApplication}
                callingLogs={callingLogs}
                onCallingStatusChange={handleCallingStatusChange}
                selectedMonth={selectedMonth}
              />
            </TabsContent>
            <TabsContent value="status" className="m-0">
              <StatusTab 
                application={displayApplication}
                auditLogs={auditLogs}
                onStatusChange={() => {}}
                onPtpDateChange={handlePtpDateChangeWithTracking}
                addAuditLog={addAuditLog}
                selectedMonth={selectedMonth}
                refetchStatusCounts={refetchStatusCounts}
              />
            </TabsContent>
            <TabsContent value="comments" className="m-0">
              <CommentsTab 
                comments={comments}
                onAddComment={handleAddComment}
              />
            </TabsContent>
            <TabsContent value="details" className="m-0">
              <DetailsTab 
                application={displayApplication}
                repaymentHistory={repaymentHistory}
                auditLogs={auditLogs}
                onVehicleStatusChange={handleVehicleStatusChange}
                monthlyData={monthlyData}
              />
            </TabsContent>
          </div>
        </Tabs>
      </div>
    </div>
  );
};

export default ApplicationDetailsPanel;

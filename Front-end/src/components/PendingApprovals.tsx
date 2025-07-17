import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible";
import { supabase } from "@/integrations/api/client";
import { useAuth } from "@/hooks/useAuth";
import { useUserProfiles } from "@/hooks/useUserProfiles";
import { toast } from "sonner";
import { format } from "date-fns";
import { CheckCircle, XCircle, Clock, ChevronDown, ChevronUp } from "lucide-react";
import { formatEmiMonth } from "@/utils/formatters";

interface StatusChangeRequest {
  id: string;
  application_id: string;
  requested_status: string;
  current_status: string;
  requested_by_user_id: string;
  requested_by_email: string | null;
  requested_by_name: string | null;
  request_timestamp: string;
  approval_status: 'pending' | 'approved' | 'rejected';
  reviewed_by_user_id: string | null;
  reviewed_by_email: string | null;
  reviewed_by_name: string | null;
  review_timestamp: string | null;
  review_comments: string | null;
  demand_date: string;
  // Application details
  applicant_name?: string;
  applicant_id?: string;
}

interface PendingApprovalsProps {
  onUpdate: () => void;
}

const PendingApprovals = ({ onUpdate }: PendingApprovalsProps) => {
  const { user } = useAuth();
  const { getUserName } = useUserProfiles();
  const [requests, setRequests] = useState<StatusChangeRequest[]>([]);
  const [loading, setLoading] = useState(false);
  const [reviewComments, setReviewComments] = useState<Record<string, string>>({});
  const [selectedRequests, setSelectedRequests] = useState<string[]>([]);
  const [bulkComments, setBulkComments] = useState("");
  const [isOpen, setIsOpen] = useState(() => {
    // Load saved state from localStorage
    const saved = localStorage.getItem('pendingApprovalsOpen');
    return saved !== null ? JSON.parse(saved) : true;
  });
  const [sortByMonth, setSortByMonth] = useState(false);

  // Save toggle state to localStorage
  useEffect(() => {
    localStorage.setItem('pendingApprovalsOpen', JSON.stringify(isOpen));
  }, [isOpen]);

  const fetchPendingRequests = async () => {
    if (!user) return;

    setLoading(true);
    try {
      // First get the status change requests
      const { data: requestsData, error: requestsError } = await supabase
        .from('status_change_requests')
        .select('*')
        .eq('approval_status', 'pending')
        .order('request_timestamp', { ascending: false });

      if (requestsError) {
        console.error('Error fetching pending requests:', requestsError);
        toast.error('Failed to fetch pending requests');
        return;
      }

      if (!requestsData || requestsData.length === 0) {
        setRequests([]);
        return;
      }

      // Get application details for each request
      const applicationIds = requestsData.map(req => req.application_id);
      const { data: applicationsData, error: applicationsError } = await supabase
        .from('applications')
        .select('applicant_id, applicant_name')
        .in('applicant_id', applicationIds);

      if (applicationsError) {
        console.error('Error fetching applications:', applicationsError);
        toast.error('Failed to fetch application details');
        return;
      }

      // Combine the data
      const requestsWithAppDetails = requestsData.map(request => {
        const appDetails = applicationsData?.find(app => app.applicant_id === request.application_id);
        return {
          ...request,
          applicant_name: appDetails?.applicant_name,
          applicant_id: appDetails?.applicant_id
        };
      });

      setRequests(requestsWithAppDetails);
    } catch (error) {
      console.error('Error fetching pending requests:', error);
      toast.error('Failed to fetch pending requests');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPendingRequests();
  }, [user]);

  const handleApproval = async (requestId: string, action: 'approved' | 'rejected') => {
    if (!user) return;

    try {
      const request = requests.find(r => r.id === requestId);
      if (!request) return;

      const comments = reviewComments[requestId] || '';

      // Update the status change request
      const { error: requestError } = await supabase
        .from('status_change_requests')
        .update({
          approval_status: action,
          reviewed_by_user_id: user.id,
          reviewed_by_email: user.email,
          reviewed_by_name: getUserName(user.id, user.email),
          review_timestamp: new Date().toISOString(),
          review_comments: comments || null,
          updated_at: new Date().toISOString()
        })
        .eq('id', requestId);

      if (requestError) {
        console.error('Error updating request:', requestError);
        toast.error('Failed to update request');
        return;
      }

      if (action === 'approved') {
        // Update field_status to the requested status
        const { error: statusError } = await supabase
          .from('field_status')
          .update({
            status: request.requested_status,
            requested_status: null,
            status_approval_needed: false,
            updated_at: new Date().toISOString()
          })
          .eq('application_id', request.application_id);

        if (statusError) {
          console.error('Error updating field status:', statusError);
          toast.error('Failed to update application status');
          return;
        }

        // Add audit log for approval
        const { error: auditError } = await supabase
          .from('audit_logs')
          .insert({
            application_id: request.application_id,
            field: 'Status',
            previous_value: `${request.current_status} (Pending Approval)`,
            new_value: request.requested_status,
            user_id: user.id,
            user_email: user.email,
            demand_date: request.demand_date
          });

        if (auditError) {
          console.error('Error adding audit log:', auditError);
        }

        toast.success(`Status change approved and updated to ${request.requested_status}`);
      } else {
        // Revert field_status to previous status
        const { error: statusError } = await supabase
          .from('field_status')
          .update({
            status: request.current_status,
            requested_status: null,
            status_approval_needed: false,
            updated_at: new Date().toISOString()
          })
          .eq('application_id', request.application_id);

        if (statusError) {
          console.error('Error reverting field status:', statusError);
          toast.error('Failed to revert application status');
          return;
        }

        // Add audit log for rejection
        const { error: auditError } = await supabase
          .from('audit_logs')
          .insert({
            application_id: request.application_id,
            field: 'Status',
            previous_value: `${request.requested_status} (Pending Approval)`,
            new_value: request.current_status,
            user_id: user.id,
            user_email: user.email,
            demand_date: request.demand_date
          });

        if (auditError) {
          console.error('Error adding audit log:', auditError);
        }

        toast.success('Status change rejected and reverted');
      }

      // Refresh the requests and trigger parent update
      await fetchPendingRequests();
      onUpdate();
    } catch (error) {
      console.error('Error processing approval:', error);
      toast.error('Failed to process approval');
    }
  };

  const handleBulkApproval = async (action: 'approved' | 'rejected') => {
    if (!user || selectedRequests.length === 0) return;

    setLoading(true);
    try {
      const selectedRequestObjects = requests.filter(r => selectedRequests.includes(r.id));
      
      for (const request of selectedRequestObjects) {
        await handleApproval(request.id, action);
      }

      setSelectedRequests([]);
      setBulkComments("");
      toast.success(`Bulk ${action} completed for ${selectedRequests.length} requests`);
    } catch (error) {
      console.error('Error in bulk approval:', error);
      toast.error('Failed to process bulk approval');
    } finally {
      setLoading(false);
    }
  };

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedRequests(requests.map(r => r.id));
    } else {
      setSelectedRequests([]);
    }
  };

  const handleSelectRequest = (requestId: string, checked: boolean) => {
    if (checked) {
      setSelectedRequests(prev => [...prev, requestId]);
    } else {
      setSelectedRequests(prev => prev.filter(id => id !== requestId));
    }
  };

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="h-5 w-5" />
            Pending Status Approvals
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-4">Loading pending requests...</div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <Collapsible open={isOpen} onOpenChange={setIsOpen}>
        <CollapsibleTrigger asChild>
          <CardHeader className="cursor-pointer hover:bg-gray-50 transition-colors">
            <CardTitle className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock className="h-5 w-5" />
                Pending Status Approvals
                {requests.length > 0 && (
                  <Badge variant="secondary" className="ml-2">
                    {requests.length}
                  </Badge>
                )}
              </div>
              {isOpen ? <ChevronUp className="h-5 w-5" /> : <ChevronDown className="h-5 w-5" />}
            </CardTitle>
          </CardHeader>
        </CollapsibleTrigger>
        
        <CollapsibleContent>
          <CardContent>
            {requests.length === 0 ? (
              <div className="text-center py-4 text-gray-500">No pending requests</div>
            ) : (
              <div className="space-y-4">
                {/* Bulk Actions */}
                <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                  <div className="flex items-center gap-4">
                    <Checkbox
                      checked={selectedRequests.length === requests.length}
                      onCheckedChange={handleSelectAll}
                    />
                    <span className="text-sm font-medium">
                      {selectedRequests.length > 0 ? `${selectedRequests.length} selected` : 'Select all'}
                    </span>
                  </div>
                  
                  {selectedRequests.length > 0 && (
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        onClick={() => handleBulkApproval('approved')}
                        className="flex items-center gap-1 bg-green-600 hover:bg-green-700"
                        disabled={loading}
                      >
                        <CheckCircle className="h-4 w-4" />
                        Bulk Approve ({selectedRequests.length})
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => handleBulkApproval('rejected')}
                        className="flex items-center gap-1"
                        disabled={loading}
                      >
                        <XCircle className="h-4 w-4" />
                        Bulk Reject ({selectedRequests.length})
                      </Button>
                    </div>
                  )}
                </div>

                {/* Table header for sorting */}
                <div className="flex font-semibold text-gray-700 border-b pb-2 mb-2">
                  <div className="w-1/4">Applicant</div>
                  <div className="w-1/4">Status Change</div>
                  <div className="w-1/4 cursor-pointer" onClick={() => setSortByMonth((prev) => !prev)}>
                    Demand Month
                    <span className="ml-1">{sortByMonth ? "▲" : "▼"}</span>
                          </div>
                  <div className="w-1/4">Actions</div>
                    </div>

                {/* Sort requests by demand month if enabled */}
                {requests
                  .slice()
                  .sort((a, b) => sortByMonth
                    ? (a.demand_date || "").localeCompare(b.demand_date || "")
                    : 0
                  )
                  .map((request) => (
                    <div key={request.id} className="flex items-center border-b py-2">
                      <div className="w-1/4">{request.applicant_name} ({request.applicant_id})</div>
                      <div className="w-1/4">{request.current_status} → {request.requested_status}</div>
                      <div className="w-1/4">{formatEmiMonth(request.demand_date)}</div>
                      <div className="w-1/4">
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        onClick={() => handleApproval(request.id, 'approved')}
                        className="flex items-center gap-1 bg-green-600 hover:bg-green-700"
                        disabled={loading}
                      >
                        <CheckCircle className="h-4 w-4" />
                        Approve
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => handleApproval(request.id, 'rejected')}
                        className="flex items-center gap-1"
                        disabled={loading}
                      >
                        <XCircle className="h-4 w-4" />
                        Reject
                      </Button>
                        </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </CollapsibleContent>
      </Collapsible>
    </Card>
  );
};

export default PendingApprovals;
